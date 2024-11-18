from django.db import migrations


def initialize_observation_level_order(apps, schema_editor):
    ObservationLevel = apps.get_model('v1', 'ObservationLevel')
    
    # Group by each possible parent type and set order
    for table_id in ObservationLevel.objects.values_list('table_id', flat=True).distinct():
        if table_id:
            for i, ol in enumerate(ObservationLevel.objects.filter(table_id=table_id)):
                ol.order = i
                ol.save()
    
    for rds_id in ObservationLevel.objects.values_list('raw_data_source_id', flat=True).distinct():
        if rds_id:
            for i, ol in enumerate(ObservationLevel.objects.filter(raw_data_source_id=rds_id)):
                ol.order = i
                ol.save()
                
    for ir_id in ObservationLevel.objects.values_list('information_request_id', flat=True).distinct():
        if ir_id:
            for i, ol in enumerate(ObservationLevel.objects.filter(information_request_id=ir_id)):
                ol.order = i
                ol.save()
                
    for analysis_id in ObservationLevel.objects.values_list('analysis_id', flat=True).distinct():
        if analysis_id:
            for i, ol in enumerate(ObservationLevel.objects.filter(analysis_id=analysis_id)):
                ol.order = i
                ol.save()

def reverse_migration(apps, schema_editor):
    ObservationLevel = apps.get_model('v1', 'ObservationLevel')
    ObservationLevel.objects.all().update(order=0)

class Migration(migrations.Migration):
    dependencies = [
        ('v1', '0046_observationlevel_order'),
    ]

    operations = [
        migrations.RunPython(initialize_observation_level_order, reverse_migration),
    ] 