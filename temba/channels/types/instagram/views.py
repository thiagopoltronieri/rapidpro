import requests
from smartmin.views import SmartFormView, SmartModelActionView

from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from temba.orgs.views import ModalMixin, OrgObjPermsMixin

from ...models import Channel
from ...views import ClaimViewMixin


class ClaimView(ClaimViewMixin, SmartFormView):
    class Form(ClaimViewMixin.Form):

        user_access_token = forms.CharField(min_length=32, required=True, help_text=_("The User Access Token"))
        fb_user_id = forms.CharField(
            required=True, help_text=_("The Facebook User ID of the admin that connected the channel")
        )
        page_name = forms.CharField(required=True, help_text=_("The name of the Facebook page"))
        page_id = forms.IntegerField(required=True, help_text="The Facebook Page ID")

        def clean(self):
            try:
                auth_token = self.cleaned_data["user_access_token"]
                name = self.cleaned_data["page_name"]
                page_id = self.cleaned_data["page_id"]
                fb_user_id = self.cleaned_data["fb_user_id"]

                app_id = settings.FACEBOOK_APPLICATION_ID
                app_secret = settings.FACEBOOK_APPLICATION_SECRET

                # get user long lived access token
                url = "https://graph.facebook.com/oauth/access_token"
                params = {
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": auth_token,
                }

                response = requests.get(url, params=params)

                if response.status_code != 200:  # pragma: no cover
                    raise Exception("Failed to get a user long lived token")

                long_lived_auth_token = response.json().get("access_token", "")

                if long_lived_auth_token == "":  # pragma: no cover
                    raise Exception("Empty user access token!")

                url = f"https://graph.facebook.com/v12.0/{fb_user_id}/accounts"
                params = {"access_token": long_lived_auth_token}

                response = requests.get(url, params=params)

                if response.status_code != 200:  # pragma: no cover
                    raise Exception("Failed to get a page long lived token")

                response_json = response.json()

                page_access_token = ""
                for elt in response_json["data"]:
                    if elt["id"] == str(page_id):
                        page_access_token = elt["access_token"]
                        name = elt["name"]
                        break

                if page_access_token == "":  # pragma: no cover
                    raise Exception("Empty page access token!")

                url = f"https://graph.facebook.com/v12.0/{page_id}/subscribed_apps"
                params = {"access_token": page_access_token}
                data = {"subscribed_fields": "messages,messaging_postbacks"}

                response = requests.post(url, data=data, params=params)

                if response.status_code != 200:  # pragma: no cover
                    raise Exception("Failed to subscribe to app for webhook events")

                self.cleaned_data["page_access_token"] = page_access_token
                self.cleaned_data["name"] = name

                url = f"https://graph.facebook.com/{page_id}?fields=instagram_business_account"
                params = {"access_token": page_access_token}

                response = requests.get(url, params=params)

                if response.status_code != 200:  # pragma: no cover
                    raise Exception("Failed to get IG user")

                response_json = response.json()
                self.cleaned_data["ig_user_id"] = response_json.get("instagram_business_account").get("id")

            except Exception:
                raise forms.ValidationError(_("Sorry your Instagram channel could not be connected. Please try again"))

            return self.cleaned_data

    form_class = Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["claim_url"] = reverse("channels.types.instagram.claim")
        context["facebook_app_id"] = settings.FACEBOOK_APPLICATION_ID
        return context

    def form_valid(self, form):
        org = self.request.user.get_org()
        page_id = form.cleaned_data["page_id"]
        page_access_token = form.cleaned_data["page_access_token"]
        name = form.cleaned_data["name"]
        ig_user_id = form.cleaned_data["ig_user_id"]

        config = {Channel.CONFIG_AUTH_TOKEN: page_access_token, Channel.CONFIG_PAGE_NAME: name, "page_id": page_id}

        self.object = Channel.create(
            org, self.request.user, None, self.channel_type, name=name, address=ig_user_id, config=config
        )

        return super().form_valid(form)


class RefreshToken(ModalMixin, OrgObjPermsMixin, SmartModelActionView):
    class Form(forms.Form):
        user_access_token = forms.CharField(min_length=32, required=True, help_text=_("The User Access Token"))
        fb_user_id = forms.CharField(
            required=True, help_text=_("The Facebook User ID of the admin that connected the channel")
        )

    slug_url_kwarg = "uuid"
    success_url = "uuid@channels.channel_read"
    form_class = Form
    permission = "channels.channel_claim"
    fields = ()
    template_name = "channels/types/instagram/refresh_token.html"
    title = _("Reconnect Facebook Page")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["refresh_url"] = reverse("channels.types.instagram.refresh_token", args=(self.object.uuid,))
        context["facebook_app_id"] = settings.FACEBOOK_APPLICATION_ID

        resp = requests.get(
            "https://graph.facebook.com/v12.0/me",
            params={"access_token": self.object.config[Channel.CONFIG_AUTH_TOKEN]},
        )

        error_connect = False
        if resp.status_code != 200:
            error_connect = True

        context["error_connect"] = error_connect

        return context

    def get_queryset(self):
        return Channel.objects.filter(is_active=True, org=self.request.user.get_org(), channel_type="IG")

    def execute_action(self):

        form = self.form
        channel = self.object

        auth_token = form.data["user_access_token"]
        fb_user_id = form.data["fb_user_id"]

        page_id = channel.config.get("page_id")

        if page_id is None:
            raise Exception("Failed to get channel page ID")

        app_id = settings.FACEBOOK_APPLICATION_ID
        app_secret = settings.FACEBOOK_APPLICATION_SECRET

        # get user long lived access token
        url = "https://graph.facebook.com/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": auth_token,
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:  # pragma: no cover
            raise Exception("Failed to get a user long lived token")

        long_lived_auth_token = response.json().get("access_token", "")

        if long_lived_auth_token == "":  # pragma: no cover
            raise Exception("Empty user access token!")

        url = f"https://graph.facebook.com/v12.0/{fb_user_id}/accounts"
        params = {"access_token": long_lived_auth_token}

        response = requests.get(url, params=params)

        if response.status_code != 200:  # pragma: no cover
            raise Exception("Failed to get a page long lived token")

        response_json = response.json()

        page_access_token = ""
        for elt in response_json["data"]:
            if elt["id"] == str(page_id):
                page_access_token = elt["access_token"]
                name = elt["name"]
                break
        if page_access_token == "":  # pragma: no cover
            raise Exception("Empty page access token!")

        url = f"https://graph.facebook.com/v12.0/{page_id}/subscribed_apps"
        params = {"access_token": page_access_token}
        data = {"subscribed_fields": "messages,messaging_postbacks"}

        response = requests.post(url, data=data, params=params)

        if response.status_code != 200:  # pragma: no cover
            raise Exception("Failed to subscribe to app for webhook events")

        channel.config[Channel.CONFIG_AUTH_TOKEN] = page_access_token
        channel.config[Channel.CONFIG_PAGE_NAME] = name
        channel.save(update_fields=["config"])
