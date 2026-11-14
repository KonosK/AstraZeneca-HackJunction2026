"""Live-model Chromium journey. Provider successes/failures are explicitly mocked."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/screenshots'
OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:5173'
results=[]

def shot(page,name):
 page.evaluate('window.scrollTo(0,0)')
 page.screenshot(path=str(OUT/name),full_page=True)

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1440,'height':900})
 page=context.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE+'/simulation')
 page.get_by_label('County context').select_option(label='Lapland')
 # Baseline flows continuously; pausing really stops the clock.
 page.get_by_role('button',name='Start simulation',exact=True).click()
 page.wait_for_function("Number(document.querySelector('[data-testid=day]').textContent)>2")
 page.get_by_role('button',name='Pause',exact=True).click()
 paused=page.get_by_test_id('day').inner_text();page.wait_for_timeout(400)
 expect(page.get_by_test_id('day')).to_have_text(paused)
 page.get_by_role('button',name='Continue simulation',exact=True).click()
 expect(page.get_by_test_id('day')).to_have_text('78',timeout=20000)
 expect(page.get_by_text('Scenario complete · day 78')).to_be_visible()
 results.append('Baseline continuously reaches day 78; play/pause works without repeated next-event clicks')
 page.get_by_role('button',name='With SILTA',exact=True).click()
 page.get_by_role('button',name='Start simulation',exact=True).click()
 expect(page.get_by_test_id('day')).to_have_text('03')
 expect(page.get_by_role('button',name='Continue simulation',exact=True)).to_have_count(0)
 page.get_by_role('button',name='Open Patient questionnaire →',exact=True).click()
 page.get_by_role('button',name='Fill demo check-in',exact=True).click()
 assert 'synthetic demo case' in page.get_by_label('Editable answer preview').input_value()
 assert page.locator('.field-row:visible').count()==0
 expect(page.get_by_role('button',name='Confirm answer preview')).to_have_count(0)
 expect(page.get_by_role('button',name='Confirm structured intake')).to_have_count(0)
 page.get_by_text('Review or correct record & travel time',exact=True).click()
 page.get_by_label('Already referred to a specialist?',exact=True).select_option('true')
 page.get_by_role('button',name='Confirm & send check-in',exact=True).click()
 expect(page.get_by_text('Resolve conflicting answers first.',exact=False)).to_be_visible()
 page.get_by_role('button',name='Keep recorded value',exact=True).click()
 page.get_by_text('Review or correct record & travel time',exact=True).click()
 page.get_by_label('Editable answer preview').fill('Synthetic check-in: about 95 minutes to reach care.')
 shot(page,'patient-questionnaire-1440.png')
 with page.expect_response(lambda r:'/analyze/patient' in r.url) as response:
  page.get_by_role('button',name='Confirm & send check-in',exact=True).click()
 assert response.value.status==200
 payload=response.value.request.post_data_json
 assert payload['symptom_severity_score']==7 and payload['travel_time_to_care_minutes']==95
 assert 'transcript' not in payload
 expect(page.get_by_text('Sent for review',exact=True)).to_be_visible()
 shot(page,'patient-submitted-1440.png')
 results.append('One patient confirmation validates provenance/conflicts, calls the real API and submits the local review')
 page.get_by_role('button',name='Continue simulation →',exact=True).click()
 expect(page.get_by_test_id('day')).to_have_text('07')
 expect(page.get_by_role('button',name='Continue simulation',exact=True)).to_have_count(0)
 page.get_by_role('button',name='Open Doctor review →',exact=True).click()
 expect(page.locator('.model-review-summary')).to_contain_text('Regional model index')
 expect(page.locator('.model-review-summary')).to_contain_text('Not individual cancer risk')
 expect(page.get_by_role('button',name='Accept selected & continue')).to_be_disabled()
 assert page.get_by_role('checkbox',name='Select proposal',exact=False).count()>=2
 page.get_by_role('button',name='Request more information',exact=True).click()
 expect(page.get_by_text('Local decision: more information.',exact=False)).to_be_visible()
 page.get_by_role('link',name='Patient',exact=True).click()
 expect(page.get_by_text('More information requested',exact=True)).to_be_visible()
 page.get_by_role('link',name='Doctor',exact=True).click()
 page.get_by_role('button',name='Reject',exact=True).click()
 expect(page.get_by_text('Local decision: rejected.',exact=False)).to_be_visible()
 page.get_by_role('button',name='Edit review note').click()
 page.get_by_label('Local review note').fill('Synthetic local review: select only the endorsed actions.')
 page.get_by_role('button',name='Save local note').click()
 page.get_by_role('checkbox',name='Select proposal 1',exact=True).check()
 page.get_by_role('checkbox',name='Select proposal 2',exact=True).check()
 shot(page,'doctor-reviewed-1440.png')
 page.get_by_role('button',name='Accept selected & continue',exact=True).click()
 expect(page.get_by_test_id('day')).to_have_text('32',timeout=10000)
 expect(page.get_by_text('Scenario complete · day 32')).to_be_visible()
 shot(page,'simulation-complete-1440.png')
 results.append('Clinician selects proposals; acceptance is a single explicit local decision and resumes to day 32')
 page.get_by_role('link',name='Dashboard',exact=True).click()
 expect(page.get_by_label('County context')).to_have_value('968')
 expect(page.locator('.county-actions > .recommendations .recommendation')).to_have_count(1)
 shot(page,'dashboard-1440.png')
 for width,height in [(1440,900),(1280,900),(390,844)]:
  page.set_viewport_size({'width':width,'height':height});boxes=[]
  for route in ['simulation','patient','doctor','dashboard']:
   page.get_by_role('link',name=route.capitalize(),exact=True).click();page.wait_for_timeout(250)
   box=page.locator('.floating-nav').bounding_box();boxes.append(box)
   assert abs(box['x']+box['width']/2-width/2)<1
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(route,width,'overflow')
   page.evaluate('window.scrollTo(0,0)')
   if route=='dashboard' and width>=1280:
    map_box=page.locator('.retained-map').bounding_box()
    for selector in ['.county-evidence','.county-actions']:
     assert page.locator(selector).bounding_box()['x']>=map_box['x']+map_box['width']
   shot(page,f'{route}-{width}.png')
  assert all(b['width']==boxes[0]['width'] and b['y']==boxes[0]['y'] for b in boxes)
 results.append('Four routes at 1440, 1280 and 390 px; consistent navigation, compact layouts and map-side actions')
 page.set_viewport_size({'width':1440,'height':900})
 page.get_by_role('link',name='Patient',exact=True).click()
 expect(page.get_by_text('Reviewed by your care team',exact=True)).to_be_visible()
 page.get_by_role('button',name='Edit check-in',exact=True).click()
 page.get_by_text('Review or correct record & travel time',exact=True).click()
 page.get_by_label('Travel to care (minutes, self-reported estimate)',exact=True).fill('100')
 page.get_by_role('link',name='Doctor',exact=True).click()
 expect(page.get_by_text('No submitted case yet',exact=True)).to_be_visible()
 results.append('Correcting submitted intake invalidates prior analysis, clinician approval and local submission')
 page.get_by_role('link',name='Patient',exact=True).click()
 page.get_by_text('Optional voice · ElevenLabs',exact=True).click()
 page.route('**/api/voice/status',lambda route:route.fulfill(status=200,content_type='application/json',body='{"configured":false}'))
 page.get_by_role('button',name='Check voice setup').click()
 expect(page.get_by_text('No ElevenLabs key is configured on this server.',exact=False)).to_be_visible()
 page.route('**/api/voice/check',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"ElevenLabs received a key ID instead of the secret key. Create a new API key."}'))
 page.get_by_role('button',name='Verify provider access').click()
 expect(page.get_by_text('ElevenLabs received a key ID instead of the secret key.',exact=False)).to_be_visible()
 page.get_by_label('Optional: I consent',exact=False).check()
 page.route('**/api/voice/tts',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Provider unavailable in this injected test"}'))
 page.get_by_role('button',name='Listen to SILTA').click()
 expect(page.get_by_text('Provider unavailable in this injected test.',exact=False)).to_be_visible()
 page.get_by_label('Editable answer preview').fill('Text fallback remains available.')
 results.append('Missing/rejected voice key and provider failure retain text and preset fallback')
 page.evaluate("() => { navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Denied','NotAllowedError'); }; }")
 page.get_by_role('button',name='Record voice answer').click()
 expect(page.get_by_text('Microphone permission denied. Type your answer below.')).to_be_visible()
 page.route('**/api/voice/stt',lambda route:route.fulfill(status=200,content_type='application/json',body='{"text":"Synthetic answer: 95 minutes."}'))
 page.evaluate("""() => { navigator.mediaDevices.getUserMedia = async () => { const ctx=new AudioContext(); const oscillator=ctx.createOscillator(); const dest=ctx.createMediaStreamDestination(); oscillator.connect(dest); oscillator.start(); window.syntheticAudioContext=ctx; return dest.stream; }; }""")
 page.get_by_role('button',name='Record voice answer').click()
 expect(page.get_by_role('button',name='Stop recording',exact=False)).to_be_visible();page.wait_for_timeout(400)
 page.get_by_role('button',name='Stop recording',exact=False).click()
 expect(page.get_by_label('Editable answer preview')).to_have_value('Synthetic answer: 95 minutes.')
 results.append('Microphone denial and generated-audio → mocked STT → editable reply are handled without paid calls')
 page.route('**/api/oncoflow/**',lambda route:route.abort())
 page.reload();expect(page.get_by_text('Backend offline / unavailable.',exact=True)).to_be_visible()
 page.get_by_role('button',name='Use explicitly recorded demo',exact=True).click()
 expect(page.get_by_text('DEMO FIXTURE — NOT LIVE MODEL RESPONSE',exact=True)).to_be_visible()
 page.get_by_role('link',name='Patient',exact=True).click()
 page.get_by_role('button',name='Fill demo check-in',exact=True).click()
 page.get_by_role('button',name='Confirm & send check-in',exact=True).click()
 expect(page.get_by_text('Sent for review',exact=True)).to_be_visible()
 results.append('Backend outage is explicit; exact-preset recorded replay works only after opt-in')
 page.get_by_role('link',name='Simulation',exact=True).click();page.get_by_role('button',name='Reset',exact=True).click()
 expect(page.get_by_test_id('day')).to_have_text('00')
 page.get_by_role('link',name='Doctor',exact=True).click();expect(page.get_by_text('No submitted case yet',exact=True)).to_be_visible()
 results.append('Reset clears the shared case, analysis, selected proposals and review')
 assert not errors,errors
 browser.close()
(ROOT/'docs/evidence/ui-results.json').write_text(json.dumps({'passed':results,'console_errors':errors},indent=2))
print('\n'.join('PASS '+result for result in results))
