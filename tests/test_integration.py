"""Integration checks with the real model and isolated provider mocks; no paid calls."""
import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import httpx
from server.app import app, NARRATION, _limits, provider_call, client, allowed_origins
from elevenlabs.core.api_error import ApiError
from mlBackend.recommendations import estimate_pathway_days, load_bundle, _county_row

class Integration(unittest.TestCase):
 def setUp(self):
  _limits.clear()
  self.c=TestClient(app)
  self.headers={'Origin':'http://127.0.0.1:8001','X-Silta-CSRF':self.c.get('/api/session').json()['token']}
 def test_actual_model_and_region(self):
  h=self.c.get('/api/oncoflow/health');self.assertEqual(h.status_code,200)
  self.assertEqual(h.json()['model']['target'],'cancer_index_age_std')
  self.assertEqual(self.c.get('/api/oncoflow/regions').json()['count'],23)
 def test_actual_error_contract(self):
  self.assertEqual(self.c.post('/api/oncoflow/analyze/region',json={'region_name':'does-not-exist'}).status_code,404)
  self.assertEqual(self.c.post('/api/oncoflow/analyze/patient',json={'patient_id':'SYNTH-TEST','region_name':'Lapland','age':78,'symptom_severity_score':11}).status_code,422)
 def test_voice_origin_and_csrf(self):
  self.assertEqual(self.c.post('/api/voice/tts',json={'text':NARRATION}).status_code,403)
  self.assertEqual(self.c.post('/api/voice/tts',json={'text':NARRATION},headers={**self.headers,'Origin':'https://unknown.example'}).status_code,403)
 def test_voice_setup_status_never_returns_credentials_or_calls_provider(self):
  for key in ['', 'synthetic-test-key-not-real']:
   with patch.dict(os.environ,{'ELEVENLABS_API_KEY':key}),patch('server.app.client') as provider:
    r=self.c.get('/api/voice/status')
   self.assertEqual(r.status_code,200)
   self.assertEqual(r.json(),{'configured':bool(key),'provider':'ElevenLabs','provider_access':'not_checked','text_fallback':True})
   provider.assert_not_called()
 def test_no_key_text_fallback(self):
  with patch.dict(os.environ,{'ELEVENLABS_API_KEY':''}):
   r=self.c.post('/api/voice/tts',json={'text':NARRATION},headers=self.headers)
  self.assertEqual(r.status_code,503);self.assertIn('text',r.json()['detail'])
 def test_only_fixed_narration(self):
  self.assertEqual(self.c.post('/api/voice/tts',json={'text':'unapproved clinical instruction'},headers=self.headers).status_code,422)
 def test_audio_format_and_size(self):
  self.assertEqual(self.c.post('/api/voice/stt',content=b'123',headers={**self.headers,'Content-Type':'text/plain'}).status_code,415)
  self.assertEqual(self.c.post('/api/voice/stt',content=b'123',headers={**self.headers,'Content-Type':'audio/webm'}).status_code,422)
  self.assertEqual(self.c.post('/api/voice/stt',content=b'x'*(4*1024*1024+1),headers={**self.headers,'Content-Type':'audio/webm'}).status_code,413)
 def test_timeout_is_safe(self):
  def failed():raise httpx.ReadTimeout('synthetic request')
  with self.assertRaises(HTTPException) as cm:provider_call(failed)
  self.assertEqual(cm.exception.status_code,504)
 def test_rate_limit_no_paid_calls(self):
  for _ in range(6):self.c.post('/api/voice/tts',json={'text':'not approved'},headers=self.headers)
  self.assertEqual(self.c.post('/api/voice/tts',json={'text':'not approved'},headers=self.headers).status_code,429)
 def test_provider_output_and_no_secrets(self):
  with patch('server.app.provider_call',return_value=b'fake-mp3-test-only'):
   r=self.c.post('/api/voice/tts',json={'text':NARRATION},headers=self.headers)
  self.assertEqual(r.status_code,200);self.assertEqual(r.headers['cache-control'],'no-store')
 def test_provider_statuses_sanitized(self):
  for status,body,expected in [(400,{'detail':{'status':'api_key_id_used_as_api_key'}},503),(401,{},503),(402,{},503),(429,{},429),(500,{},502)]:
   def failed():raise ApiError(status_code=status,body=body)
   with self.assertRaises(HTTPException) as cm:provider_call(failed)
   self.assertEqual(cm.exception.status_code,expected)
 def test_stt_route_with_mocked_official_adapter(self):
  fake=MagicMock();fake.speech_to_text.convert.return_value=type('Result',(),{'text':'Synthetic answer: 95 minutes.'})()
  with patch('server.app.client',return_value=fake):
   r=self.c.post('/api/voice/stt',content=b'x'*1000,headers={**self.headers,'Content-Type':'audio/webm'})
  self.assertEqual(r.status_code,200);self.assertEqual(r.json()['text'],'Synthetic answer: 95 minutes.')
  self.assertEqual(fake.speech_to_text.convert.call_args.kwargs['model_id'],'scribe_v2')
 def test_private_production_gate(self):
  import base64
  with patch.dict(os.environ,{'APP_ENV':'production','DEMO_ACCESS_TOKEN':'test-only-local-password'}):
   self.assertEqual(self.c.get('/api/oncoflow/health').status_code,401)
   auth=base64.b64encode(b'demo:test-only-local-password').decode()
   self.assertEqual(self.c.get('/api/oncoflow/health',headers={'Authorization':'Basic '+auth}).status_code,200)
 def test_provider_account_check_never_returns_key_or_generates_audio(self):
  fake=MagicMock();fake.user.subscription.get.return_value=type('Subscription',(),{'character_count':100,'character_limit':1000})()
  with patch('server.app.client',return_value=fake):
   r=self.c.post('/api/voice/check',headers=self.headers)
  self.assertEqual(r.status_code,200);self.assertEqual(r.json()['remaining_characters'],900)
  self.assertEqual(set(r.json()),{'authenticated','account_lookup','remaining_characters','message'})
  fake.text_to_speech.convert.assert_not_called();fake.speech_to_text.convert.assert_not_called()
 def test_provider_account_check_rejected_key_is_actionable(self):
  fake=MagicMock();fake.user.subscription.get.side_effect=ApiError(status_code=400,body={'detail':{'status':'api_key_id_used_as_api_key'}})
  with patch('server.app.client',return_value=fake):r=self.c.post('/api/voice/check',headers=self.headers)
  self.assertEqual(r.status_code,503);self.assertIn('Create a new API key',r.json()['detail'])
 def test_key_whitespace_and_accidental_quotes_are_normalized(self):
  with patch.dict(os.environ,{'ELEVENLABS_API_KEY':' "synthetic-test-only" '}),patch('server.app.ElevenLabs') as sdk:
   client()
  sdk.assert_called_once_with(api_key='synthetic-test-only',timeout=25)
 def test_public_readiness_keeps_production_api_private(self):
  with patch.dict(os.environ,{'APP_ENV':'production','DEMO_ACCESS_TOKEN':'','VERCEL':'1'}):
   self.assertEqual(self.c.get('/healthz').json(),{'status':'ok'})
   self.assertEqual(self.c.get('/api/oncoflow/health').status_code,401)
 def test_vercel_and_explicit_origins(self):
  with patch.dict(os.environ,{'APP_ORIGINS':'https://custom.example/','VERCEL_URL':'preview.vercel.app','VERCEL_PROJECT_PRODUCTION_URL':'production.vercel.app'}):
   self.assertIn('https://preview.vercel.app',allowed_origins());self.assertIn('https://production.vercel.app',allowed_origins());self.assertIn('https://custom.example',allowed_origins())
 def test_known_severity_zero_backend_discrepancy(self):
  # Characterization test: flag for teammate review, never compensate in the client.
  row=_county_row(load_bundle(),'Lapland')
  self.assertEqual(estimate_pathway_days(row,{'age':78,'symptom_severity_score':0}),estimate_pathway_days(row,{'age':78,'symptom_severity_score':5}))

if __name__=='__main__':unittest.main(verbosity=2)
