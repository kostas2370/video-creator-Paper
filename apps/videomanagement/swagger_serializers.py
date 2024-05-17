from rest_framework import serializers


class GenerateSerializer(serializers.Serializer):

    message = serializers.CharField(required = True, max_length = 2000)
    template_id = serializers.CharField(required = False, max_length = 20, default = "")
    voice_id = serializers.CharField(required = False, max_length = 20, default=None)
    gpt_model = serializers.ChoiceField(required = False, choices = ["gpt-3.5-turbo", "gpt-4"], default = "gpt-4")
    images = serializers.ChoiceField(required = False, choices = ["AI", "WEB", False], default = "WEB")
    avatar_selection = serializers.CharField(required = False, max_length = 30, default = "no_avatar")
    style = serializers.ChoiceField(required = False, choices = ["vivid", "natural"], default = "vivid")
    music = serializers.CharField(required = False, max_length = 500)
    target_audience = serializers.CharField(required = False, max_length = 30, min_length = 0, default = "")
    background = serializers.CharField(required = False, max_length = 10, default = None)
    intro = serializers.CharField(required = False, max_length = 10, default = None)
    outro = serializers.CharField(required = False, max_length = 10, default = None)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class DownloadPlaylistSerializer(serializers.Serializer):

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    link = serializers.URLField(required = True)
    category = serializers.ChoiceField(choices = ["Educational", "Gaming", "Advertisement", "Story", "Other"])


class SceneUpdateSerializer(serializers.Serializer):

    text = serializers.CharField(required = True, max_length = 2000)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

