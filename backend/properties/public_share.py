"""Read-only, public landing pages for shared, currently published listings."""
from urllib.parse import urlsplit

from django.shortcuts import render
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .models import Property, PropertyPhoto


@require_safe
@never_cache
def shared_property(request, pk):
    # Never use a staff-expanded queryset or expose private model/serializer fields.
    listing = Property.objects.filter(pk=pk, status=Property.STATUS_PUBLISHED).first()
    if listing is None:
        return render(request, 'properties/shared_property.html', {'unavailable': True}, status=404)

    photos = []
    for photo in listing.photos.filter(
        quality_status=PropertyPhoto.QualityStatus.ACCEPTED,
    ).exclude(image='').order_by('-is_cover', 'id')[:12]:
        url = request.build_absolute_uri(photo.image.url)
        if urlsplit(url).scheme in ('https', 'http'):
            photos.append(url)

    location = ', '.join(filter(None, (listing.estate, listing.town, listing.county)))
    price = f'KES {listing.price:,.0f}'
    if listing.listing_type == Property.LISTING_RENT:
        price += ' / month'
    # Pass an explicit public projection, not a model with owner/contact/address fields.
    return render(request, 'properties/shared_property.html', {
        'title': listing.title,
        'description': listing.description,
        'summary': strip_tags(f'{price} · {location}. {listing.description}')[:220],
        'location': location,
        'price': price,
        'property_type': listing.get_property_type_display(),
        'listing_type': listing.get_listing_type_display(),
        'bedrooms': listing.bedrooms,
        'bathrooms': listing.bathrooms,
        'photos': photos,
        'reference': f'PH-PROPERTY-{listing.pk}',
        'canonical': f'https://patahao.app{reverse("shared-property", args=[listing.pk])}',
    })
