import django_filters

from blood.models import BloodRequest


class BloodRequestFilter(django_filters.FilterSet):
    blood_group = django_filters.CharFilter(method="filter_blood_group")

    province = django_filters.CharFilter(
        field_name="medical_center__province",
        lookup_expr="iexact",
    )

    class Meta:
        model = BloodRequest
        fields = ["blood_group", "province"]

    BLOOD_GROUP_MAP = {
        "a+": "A+",
        "a-": "A-",
        "b+": "B+",
        "b-": "B-",
        "ab+": "AB+",
        "ab-": "AB-",
        "o+": "O+",
        "o-": "O-",
        "a_positive": "A+",
        "a_negative": "A-",
        "b_positive": "B+",
        "b_negative": "B-",
        "ab_positive": "AB+",
        "ab_negative": "AB-",
        "o_positive": "O+",
        "o_negative": "O-",
    }

    def filter_blood_group(self, queryset, name, value):
        value = value.strip().lower()
        value = self.BLOOD_GROUP_MAP.get(value, value.upper())
        return queryset.filter(blood_group=value)
