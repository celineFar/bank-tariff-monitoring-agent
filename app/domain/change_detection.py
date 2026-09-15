from app.domain.models import TariffChange, TariffSnapshot


def compare_snapshots(
    previous: TariffSnapshot | None, current: TariffSnapshot
) -> list[TariffChange]:
    if previous is None:
        return []
    changes: list[TariffChange] = []
    previous_fields = previous.tariff.model_dump()
    current_fields = current.tariff.model_dump()
    for field_name, current_field in current_fields.items():
        previous_value = previous_fields[field_name]["normalized_value"]
        current_value = current_field["normalized_value"]
        if previous_value != current_value:
            changes.append(
                TariffChange(
                    field=field_name, previous=previous_value, current=current_value
                )
            )
    return changes
