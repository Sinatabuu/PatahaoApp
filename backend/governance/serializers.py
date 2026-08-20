from rest_framework import serializers


class StaffDealGovernanceDecisionSerializer(
    serializers.Serializer,
):
    decision = serializers.ChoiceField(
        choices=[
            ("keep_blocked", "Keep blocked"),
            ("return_to_partner", "Return to partner"),
            ("resolve", "Resolve"),
        ],
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )