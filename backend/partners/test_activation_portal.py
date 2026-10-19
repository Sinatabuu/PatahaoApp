from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from partners import test_training_portal as helpers
from partners.models import Partner, PartnerActivation, TrainingEnrollment, TrainingEvent
from properties.models import Property
from governance.services import enforce_partner_operational_access
from rest_framework.exceptions import ValidationError

BASE, ORIGIN = helpers.BASE, helpers.ORIGIN


class PartnerActivationTests(TestCase):
    setUpTestData = classmethod(helpers.TrainingPortalTests.setUpTestData.__func__)
    auth = helpers.TrainingPortalTests.auth
    enroll = helpers.TrainingPortalTests.enroll
    complete = helpers.TrainingPortalTests.complete
    decide = helpers.TrainingPortalTests.decide

    def setUp(self):
        helpers.TrainingPortalTests.setUp(self)
        self.record=self.complete(self.enroll())
        self.auth(self.supervisor)
        response=self.decide(self.record);self.assertEqual(response.status_code,200,response.data)
        self.record=response.data
        self.user=User.objects.create_user(username='applicant',email='applicant@example.test',phone_number='0712345678',full_name='Trainee Test',password='AccountPassword123!')
        self.supervisor.user_permissions.add(Permission.objects.get(codename='activate_trained_partner',content_type__app_label='partners'))
        self.auth(self.supervisor)
        self.url=BASE+f'enrollments/{self.record["id"]}/activation/'

    def activate(self,**changes):
        return self.client.post(self.url,{'expected_updated_at':self.record['updated_at'],'user_id':self.user.pk,'account_confirmed':True,'no_cash_confirmed':True,**changes},format='json',**ORIGIN)

    def test_activate_existing_account_and_create_draft_without_publication(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.get('/api/partner/properties/').status_code,403)
        self.assertEqual(self.client.post('/api/properties/',{},format='json').status_code,403)
        self.client.force_authenticate(user=None);self.auth(self.supervisor)
        prepared=self.client.get(self.url,**ORIGIN);self.assertEqual(prepared.status_code,200)
        self.assertEqual(prepared.data['account']['id'],self.user.pk);self.assertEqual(prepared.data['issues'],[])
        response=self.activate();self.assertEqual(response.status_code,201,response.data)
        self.user.refresh_from_db();self.assertEqual(self.user.role,'partner')
        self.assertTrue(self.user.check_password('AccountPassword123!'))
        partner=Partner.objects.get(user=self.user)
        self.assertTrue(partner.is_verified);self.assertEqual(partner.phone_number,'254712345678')
        self.assertEqual(partner.verified_by,self.supervisor)
        self.assertEqual(PartnerActivation.objects.get().enrollment.application,self.application)
        self.assertEqual(TrainingEvent.objects.filter(action='Partner activated').count(),1)
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.get('/api/partner/properties/').status_code,200)
        self.assertEqual(self.client.get('/api/auth/me/').data['role'],'partner')
        response=self.client.post('/api/partner/properties/',{'title':'New partner draft','description':'Test property description','property_type':'house','listing_type':'rent','price':'20000','county':'Nairobi','town':'Roysambu','estate':'Test','status':'published'},format='json')
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(Property.objects.get().status,'draft')
        self.assertEqual(Property.objects.get().partner,partner)
        property_id=Property.objects.get().pk
        self.assertEqual(self.client.post('/api/properties/',{},format='json').status_code,403)
        self.assertEqual(self.client.patch(f'/api/properties/{property_id}/',{'status':'published'},format='json').status_code,403)
        self.assertEqual(self.client.delete(f'/api/properties/{property_id}/').status_code,403)

    def test_separate_activation_permission_required(self):
        for user in (self.trainer,self.reader):
            self.auth(user);self.assertEqual(self.client.get(self.url,**ORIGIN).status_code,403)
            self.assertEqual(self.activate().status_code,403)
        self.assertFalse(Partner.objects.exists())

    def test_uncertified_incomplete_closed_and_stale_rejected(self):
        enrollment=TrainingEnrollment.objects.get(pk=self.record['id'])
        enrollment.state='enrolled';enrollment.save()
        self.assertEqual(self.activate().status_code,409)
        self.record['updated_at']=enrollment.updated_at
        self.assertEqual(self.activate().status_code,400)
        enrollment.state='certified';enrollment.identity_checked=False;enrollment.save()
        self.record['updated_at']=enrollment.updated_at
        self.assertEqual(self.activate().status_code,400)
        enrollment.identity_checked=True;enrollment.save();self.record['updated_at']=enrollment.updated_at
        self.application.status='declined';self.application.save()
        self.assertEqual(self.activate().status_code,400)
        self.assertFalse(Partner.objects.exists())

    def test_confirmations_and_wrong_account_rejected(self):
        self.assertEqual(self.activate(no_cash_confirmed=False).status_code,400)
        self.assertEqual(self.activate(account_confirmed=False).status_code,400)
        other=User.objects.create_user(username='other',email='other@example.test',phone_number='0799999999')
        self.assertEqual(self.activate(user_id=other.pk).status_code,400)
        self.assertFalse(Partner.objects.exists())

    def test_no_account_duplicate_phone_inactive_and_privileged_accounts_blocked(self):
        self.user.phone_number='0799999999';self.user.save()
        self.assertIsNone(self.client.get(self.url,**ORIGIN).data['account'])
        self.assertEqual(self.activate().status_code,400)
        self.user.phone_number='0712345678';self.user.save()
        duplicate=User.objects.create_user(username='duplicate',email='duplicate@example.test',phone_number='+254 712 345 678')
        self.assertEqual(self.activate().status_code,400);duplicate.delete()
        self.user.is_active=False;self.user.save();self.assertEqual(self.activate().status_code,400)
        self.user.is_active=True;self.user.is_staff=True;self.user.save();self.assertEqual(self.activate().status_code,400)
        self.assertFalse(Partner.objects.exists())

    def test_existing_suspended_profile_is_never_reactivated(self):
        partner=Partner.objects.create(user=self.user,business_name='Existing',is_active=False,verification_status='suspended')
        self.assertEqual(self.activate().status_code,400)
        partner.refresh_from_db();self.assertFalse(partner.is_active);self.assertEqual(partner.verification_status,'suspended')

    def test_retry_does_not_duplicate_or_reactivate_suspended_partner(self):
        self.assertEqual(self.activate().status_code,201)
        partner=Partner.objects.get();partner.is_active=False;partner.save()
        response=self.activate();self.assertEqual(response.status_code,200,response.data)
        partner.refresh_from_db();self.assertFalse(partner.is_active)
        self.assertEqual(Partner.objects.count(),1);self.assertEqual(PartnerActivation.objects.count(),1)

    def test_audit_failure_rolls_back_role_profile_and_activation(self):
        with patch('partners.activation_portal.audit',side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):self.activate()
        self.user.refresh_from_db();self.assertEqual(self.user.role,'customer')
        self.assertFalse(Partner.objects.exists());self.assertFalse(PartnerActivation.objects.exists())

    def test_activated_training_cannot_be_reopened_or_withdrawn(self):
        self.activate();self.record=self.client.get(BASE+f'enrollments/{self.record["id"]}/',**ORIGIN).data
        self.assertEqual(self.record['state_label'],'Partner activated')
        self.assertEqual(self.decide(self.record,'reopen').status_code,400)
        self.assertEqual(self.decide(self.record,'withdraw').status_code,400)
        self.application.refresh_from_db()
        response=self.client.patch(f'/api/staff/onboarding/applications/{self.application.pk}/',{'status':'declined','office_appointment':self.application.office_appointment,'expected_updated_at':self.application.updated_at,'action':'closed'},format='json',**ORIGIN)
        self.assertEqual(response.status_code,400)

    def test_defense_in_depth_blocks_invalidated_certification(self):
        self.activate();partner=Partner.objects.get()
        TrainingEnrollment.objects.filter(pk=self.record['id']).update(state='withdrawn')
        with self.assertRaises(ValidationError):enforce_partner_operational_access(partner,operation='post_property')
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.get('/api/partner/properties/').status_code,400)

    def test_status_shows_activation_without_private_account_details(self):
        self.activate()
        response=self.client.post('/api/partner-applications/status/',{'reference':self.application.reference,'phone_number':self.application.phone_number},format='json',**ORIGIN)
        self.assertEqual(response.data['status'],'Partner activated')
        self.assertIn('partner_code',response.data)
        self.assertNotIn('username',response.data);self.assertNotIn('user_id',response.data)
