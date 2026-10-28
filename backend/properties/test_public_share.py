from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Property, PropertyPhoto


class PublicPropertyShareTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.listing = Property.objects.create(
            title='Sunny Roysambu Apartment', property_type='apartment', listing_type='rent',
            price=Decimal('25000.00'), county='Nairobi', town='Roysambu', estate='Garden Estate',
            bedrooms=2, bathrooms=1, address='PRIVATE exact address', latitude=Decimal('-1.123456'),
            longitude=Decimal('36.654321'), description='Bright rooms with a balcony.',
            verification_return_reason='PRIVATE verification note', status='draft')
        Property.objects.filter(pk=cls.listing.pk).update(status='published')

    def url(self):
        return reverse('shared-property', args=[self.listing.pk])

    def test_public_projection_metadata_and_private_cache(self):
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        for text in ('Sunny Roysambu Apartment', 'KES 25,000 / month', 'Garden Estate, Roysambu, Nairobi',
                     'Bright rooms with a balcony.', 'https://play.google.com/store/apps/details?id=app.patahao',
                     f'https://patahao.app{self.url()}', 'property="og:title"'):
            self.assertContains(r, text)
        for text in ('PRIVATE exact address', 'PRIVATE verification note', '-1.123456', '36.654321'):
            self.assertNotContains(r, text)
        self.assertIn('no-store', r['Cache-Control'])
        self.assertIn('private', r['Cache-Control'])

    def test_nonpublic_or_missing_is_generic_even_for_staff(self):
        self.client.force_login(get_user_model().objects.create_user(username='staff', is_staff=True))
        for state in ('draft', 'pending', 'reserved', 'sold', 'rented', 'archived'):
            Property.objects.filter(pk=self.listing.pk).update(status=state)
            r = self.client.get(self.url())
            self.assertEqual(r.status_code, 404)
            self.assertNotContains(r, self.listing.title, status_code=404)
            self.assertContains(r, 'This listing is no longer available.', status_code=404)
            self.assertIn('no-store', r['Cache-Control'])
        self.assertEqual(self.client.get('/p/999999999/').status_code, 404)

    def test_same_link_stops_rendering_after_removal(self):
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        Property.objects.filter(pk=self.listing.pk).update(status='archived')
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_user_text_escaped_in_body_and_metadata(self):
        Property.objects.filter(pk=self.listing.pk).update(title='<script>alert(1)</script>', description='" onload="alert(2)<img src=x>')
        r = self.client.get(self.url())
        self.assertNotContains(r, '<script>')
        self.assertNotContains(r, '<img src=x>')
        self.assertContains(r, '&lt;script&gt;')
        self.assertContains(r, '&quot; onload=&quot;alert(2)&lt;img src=x&gt;')

    def test_accepted_photos_only_and_cover_first(self):
        PropertyPhoto.objects.bulk_create([
            PropertyPhoto(property=self.listing, image='property_photos/regular.jpg'),
            PropertyPhoto(property=self.listing, image='property_photos/cover.jpg', is_cover=True),
            PropertyPhoto(property=self.listing, image='property_photos/review.jpg', quality_status='needs_review')])
        with patch('django.core.files.storage.default_storage.url', side_effect=lambda name: '/media/'+name):
            r = self.client.get(self.url())
        content = r.content.decode()
        self.assertIn('cover.jpg', content)
        self.assertIn('regular.jpg', content)
        self.assertNotIn('review.jpg', content)
        self.assertLess(content.index('cover.jpg'), content.index('regular.jpg'))

    def test_head_allowed_and_post_cannot_mutate(self):
        self.assertEqual(self.client.head(self.url()).status_code, 200)
        self.assertEqual(self.client.post(self.url()).status_code, 405)
        self.assertEqual(Property.objects.count(), 1)
