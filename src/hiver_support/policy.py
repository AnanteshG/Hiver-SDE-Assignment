"""Provisional Apple-support intents and deterministic automation policy."""
import re

INTENTS = {
    'account_access': 'Apple ID, authentication, locked accounts or passwords',
    'billing_purchase': 'Charges, subscriptions, refunds and purchases',
    'battery_power': 'Battery life, charging, overheating or power',
    'connectivity': 'Wi-Fi, Bluetooth, cellular and network connection',
    'software_update': 'Operating system updates, installation and software bugs',
    'hardware_repair': 'Physical damage, broken components, repairs and warranty',
    'app_service': 'Apps and services such as music, photos and cloud storage',
    'other_unclear': 'Unsupported, ambiguous or insufficiently specified request',
}
PATTERNS = {
    'account_access': r'apple id|password|log.?in|sign.?in|locked|hacked|verification',
    'billing_purchase': r'refund|charg(?:ed|es)|billing|payment|subscription|purchase|money',
    'battery_power': r'battery|charg(?:ing|er)|overheat|power|turn on|dies|drain',
    'connectivity': r'wi.?fi|bluetooth|network|cellular|signal|internet|connect',
    'software_update': r'update|upgrade|ios|install|version|reboot|restart',
    'hardware_repair': r'broken|crack|repair|warranty|screen|button|damage|speaker',
    'app_service': r'app|music|icloud|photo|itunes|safari|storage|imessage',
}


def classify(text):
    counts = {intent: len(re.findall(r'\b(?:'+pattern+r')\b', text.lower())) for intent, pattern in PATTERNS.items()}
    return max(counts, key=counts.get) if max(counts.values(), default=0) else 'other_unclear'


def gates(example, intent, evidence, reply, supported, threshold=0.3):
    text = example['text'].lower()
    failures = []
    if intent == 'other_unclear':
        failures.append('intent_unclear')
    if example.get('context_incomplete') or len(text.split()) < 5:
        failures.append('context_insufficient')
    if intent in {'account_access', 'billing_purchase', 'hardware_repair'} or re.search(r'\brefund|\bcharged\b|\bbilling\b|\bpassword\b|\bwarranty\b|\bcancel.{0,25}subscription', text):
        failures.append('account_or_specialist_required')
    if re.search(r'smoke|fire|burn(?:ing|t)|swoll|injur|stolen|hacked|fraud|suicid', text):
        failures.append('sensitive_or_safety_issue')
    if not evidence or evidence[0]['score'] < threshold:
        failures.append('evidence_insufficient')
    if not supported:
        failures.append('support_not_established')
    if re.search(r"(?:i|we)(?:'ve| have)? (?:checked|refunded|cancelled|canceled|updated your|reset your)|(?:send|share|provide).{0,45}(?:password|credit card|card number|verification code|email|phone number|serial number)", reply, re.I):
        failures.append('prohibited_claim_or_request')
    if re.search(r'\bdm\b|direct message|\[link\]|\[email\]|\[number\]', reply, re.I):
        failures.append('private_channel_or_redacted_instruction')
    if re.search(r'(?:updat\w*|upgrad\w*) (?:it |your device )?to (?:ios|version)\s*\d|(?:released|fixed).{0,40}(?:this week|today|yesterday)|latest (?:ios|version)', reply, re.I):
        failures.append('time_sensitive_advice')
    return {'decision': 'escalate' if failures else 'auto_handle', 'reason_codes': failures or ['supported_low_risk_response'],
            'reason': '; '.join(code.replace('_', ' ') for code in failures) if failures else 'Supported next response; no account action or sensitive request identified.'}
