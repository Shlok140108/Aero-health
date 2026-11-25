import os
from html import escape
from django.conf import settings

class DeliveryNotConfigured(RuntimeError): pass

def _setting(name, env): return getattr(settings,name,None) or os.environ.get(env)


class PushSender:
    def _get_firebase_app(self):
        import firebase_admin
        from firebase_admin import credentials

        try:
            return firebase_admin.get_app()
        except ValueError:
            path = _setting(
                "ALERTS_FCM_CREDENTIALS",
                "FIREBASE_SERVICE_ACCOUNT_FILE"
            )

            if not path:
                raise DeliveryNotConfigured(
                    "Configure FIREBASE_SERVICE_ACCOUNT_FILE"
                )

            return firebase_admin.initialize_app(
                credentials.Certificate(path)
            )

    def send(self, profile, msg):
        if not profile.fcm_token:
            raise DeliveryNotConfigured(
                "No FCM device token registered"
            )

        try:
            from firebase_admin import messaging
            from firebase_admin import exceptions

            self._get_firebase_app()

            message = messaging.Message(
                notification=messaging.Notification(
                    title=msg.title,
                    body=msg.body
                ),
                data={
                    "type": "aerohealth_alert",
                    "click_action": "OPEN_AEROHEALTH"
                },
                token=profile.fcm_token
            )

            return messaging.send(message)

        except ImportError as exc:
            raise DeliveryNotConfigured(
                "Install firebase-admin"
            ) from exc

        except Exception as exc:
            # Invalid or expired device tokens should not remain active.
            from firebase_admin import messaging

            if isinstance(
                exc,
                messaging.UnregisteredError
            ):
                profile.fcm_token = ""
                profile.push_enabled = False
                profile.save(
                    update_fields=["fcm_token", "push_enabled"]
                )

            raise


class TwilioSender:
    def _client(self):
        try: from twilio.rest import Client
        except ImportError as exc: raise DeliveryNotConfigured("Install twilio to enable SMS/voice") from exc
        sid=_setting("ALERTS_TWILIO_SID","TWILIO_ACCOUNT_SID"); token=_setting("ALERTS_TWILIO_TOKEN","TWILIO_AUTH_TOKEN"); sender=_setting("ALERTS_TWILIO_FROM","TWILIO_FROM_NUMBER")
        if not (sid and token and sender): raise DeliveryNotConfigured("Configure Twilio SID, token and sender number")
        return Client(sid,token),sender
    def sms(self,profile,msg):
        client,sender=self._client(); return client.messages.create(to=profile.phone,from_=sender,body=msg.body).sid
    def voice(self,profile,msg):
        client,sender=self._client(); langs={"en":"en-IN","hi":"hi-IN","mr":"mr-IN","ta":"ta-IN","bn":"bn-IN"}
        twiml=f'<Response><Say language="{langs.get(profile.alert_language,"en-IN")}">{escape(msg.body)}</Say></Response>'
        return client.calls.create(to=profile.phone,from_=sender,twiml=twiml).sid

_twilio=TwilioSender()
def send_via(channel,profile,msg):
    if channel=="push": return PushSender().send(profile,msg)
    if channel=="sms": return _twilio.sms(profile,msg)
    if channel=="voice": return _twilio.voice(profile,msg)
    raise ValueError("Unknown notification channel")
