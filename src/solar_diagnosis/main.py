from solar_diagnosis.alerts import detect_alert
from solar_diagnosis.data_source import (
    get_sample_investigation_data,
    get_sample_records,
)
from solar_diagnosis.investigation import investigate


def run(client=None):
    plant_id = "plant-17"
    records = get_sample_records(plant_id)
    alert = detect_alert(records, plant_id)
    print("Alert detector:", alert)

    report = None
    if alert["status"] == "alert":
        report = investigate(
            alert,
            get_sample_investigation_data(),
            client=client,
        )
        print("Investigation:", report)

    return {"alert": alert, "report": report}


if __name__ == "__main__":
    run()
