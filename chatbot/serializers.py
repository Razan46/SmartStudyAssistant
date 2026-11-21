from rest_framework import serializers


class ChatParametersSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=("add_task", "list_tasks", "complete_task", "study_guide", "study_plan"),
        required=False,
    )
    task = serializers.CharField(max_length=300, required=False, allow_blank=False)
    task_id = serializers.IntegerField(min_value=1, required=False)
    topic = serializers.CharField(max_length=200, required=False, allow_blank=False)
    available_minutes = serializers.IntegerField(min_value=15, max_value=600, required=False)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, allow_blank=False)
    parameters = ChatParametersSerializer(required=False)
