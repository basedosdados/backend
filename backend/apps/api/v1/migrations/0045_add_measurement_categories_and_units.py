# -*- coding: utf-8 -*-
from django.db import migrations

def create_categories_and_units(apps, schema_editor):
    MeasurementUnitCategory = apps.get_model('v1', 'MeasurementUnitCategory')
    MeasurementUnit = apps.get_model('v1', 'MeasurementUnit')
    
    # Create categories
    categories = {
        'distance': {
            'name': 'Distância',
            'name_pt': 'Distância',
            'name_en': 'Distance',
            'name_es': 'Distancia'
        },
        'area': {
            'name': 'Área',
            'name_pt': 'Área',
            'name_en': 'Area',
            'name_es': 'Área'
        },
        'mass': {
            'name': 'Massa',
            'name_pt': 'Massa',
            'name_en': 'Mass',
            'name_es': 'Masa'
        },
        'volume': {
            'name': 'Volume',
            'name_pt': 'Volume',
            'name_en': 'Volume',
            'name_es': 'Volumen'
        },
        'energy': {
            'name': 'Energia',
            'name_pt': 'Energia',
            'name_en': 'Energy',
            'name_es': 'Energía'
        },
        'people': {
            'name': 'Pessoas',
            'name_pt': 'Pessoas',
            'name_en': 'People',
            'name_es': 'Personas'
        },
        'currency': {
            'name': 'Moeda',
            'name_pt': 'Moeda',
            'name_en': 'Currency',
            'name_es': 'Moneda'
        },
        'economics': {
            'name': 'Economia',
            'name_pt': 'Economia',
            'name_en': 'Economics',
            'name_es': 'Economía'
        },
        'datetime': {
            'name': 'Data/Hora',
            'name_pt': 'Data/Hora',
            'name_en': 'Date/Time',
            'name_es': 'Fecha/Hora'
        },
        'percentage': {
            'name': 'Porcentagem',
            'name_pt': 'Porcentagem',
            'name_en': 'Percentage',
            'name_es': 'Porcentaje'
        }
    }
    
    category_objects = {}
    for slug, names in categories.items():
        category = MeasurementUnitCategory.objects.create(
            slug=slug,
            name=names['name'],
            name_pt=names['name_pt'],
            name_en=names['name_en'],
            name_es=names['name_es']
        )
        category_objects[slug] = category

    # Define units with their categories and translations
    units = {
        # Distance
        'kilometer': {'category': 'distance', 'name': 'Kilometer', 'name_pt': 'Quilômetro', 'name_en': 'Kilometer', 'name_es': 'Kilómetro', 'tex': 'km'},
        'meter': {'category': 'distance', 'name': 'Meter', 'name_pt': 'Metro', 'name_en': 'Meter', 'name_es': 'Metro', 'tex': 'm'},
        'centimeter': {'category': 'distance', 'name': 'Centimeter', 'name_pt': 'Centímetro', 'name_en': 'Centimeter', 'name_es': 'Centímetro', 'tex': 'cm'},
        'mile': {'category': 'distance', 'name': 'Mile', 'name_pt': 'Milha', 'name_en': 'Mile', 'name_es': 'Milla', 'tex': 'mi'},
        'foot': {'category': 'distance', 'name': 'Foot', 'name_pt': 'Pé', 'name_en': 'Foot', 'name_es': 'Pie', 'tex': 'pé'},
        'inch': {'category': 'distance', 'name': 'Inch', 'name_pt': 'Polegada', 'name_en': 'Inch', 'name_es': 'Pulgada', 'tex': 'polegada'},
        
        # Area
        'kilometer2': {'category': 'area', 'name': 'Square Kilometer', 'name_pt': 'Quilômetro Quadrado', 'name_en': 'Square Kilometer', 'name_es': 'Kilómetro Cuadrado', 'tex': 'km^2'},
        'meter2': {'category': 'area', 'name': 'Square Meter', 'name_pt': 'Metro Quadrado', 'name_en': 'Square Meter', 'name_es': 'Metro Cuadrado', 'tex': 'm^2'},
        'centimeter2': {'category': 'area', 'name': 'Square Centimeter', 'name_pt': 'Centímetro Quadrado', 'name_en': 'Square Centimeter', 'name_es': 'Centímetro Cuadrado', 'tex': 'cm^2'},
        'hectare': {'category': 'area', 'name': 'Hectare', 'name_pt': 'Hectare', 'name_en': 'Hectare', 'name_es': 'Hectárea', 'tex': 'ha'},
        'acre': {'category': 'area', 'name': 'Acre', 'name_pt': 'Acre', 'name_en': 'Acre', 'name_es': 'Acre', 'tex': 'ac'},
        'mile2': {'category': 'area', 'name': 'Square Mile', 'name_pt': 'Milha Quadrada', 'name_en': 'Square Mile', 'name_es': 'Milla Cuadrada', 'tex': 'mi^2'},
        'foot2': {'category': 'area', 'name': 'Square Foot', 'name_pt': 'Pé Quadrado', 'name_en': 'Square Foot', 'name_es': 'Pie Cuadrado', 'tex': 'ft^2'},
        'inch2': {'category': 'area', 'name': 'Square Inch', 'name_pt': 'Polegada Quadrada', 'name_en': 'Square Inch', 'name_es': 'Pulgada Cuadrada', 'tex': 'in^2'},
        
        # Mass
        'ton': {'category': 'mass', 'name': 'Ton', 'name_pt': 'Tonelada', 'name_en': 'Ton', 'name_es': 'Tonelada', 'tex': 'ton'},
        'kilogram': {'category': 'mass', 'name': 'Kilogram', 'name_pt': 'Quilograma', 'name_en': 'Kilogram', 'name_es': 'Kilogramo', 'tex': 'kg'},
        'gram': {'category': 'mass', 'name': 'Gram', 'name_pt': 'Grama', 'name_en': 'Gram', 'name_es': 'Gramo', 'tex': 'g'},
        'miligram': {'category': 'mass', 'name': 'Milligram', 'name_pt': 'Miligrama', 'name_en': 'Milligram', 'name_es': 'Miligramo', 'tex': 'mg'},
        'ounce': {'category': 'mass', 'name': 'Ounce', 'name_pt': 'Onça', 'name_en': 'Ounce', 'name_es': 'Onza', 'tex': 'oz'},
        
        # Volume
        'gallon': {'category': 'volume', 'name': 'Gallon', 'name_pt': 'Galão', 'name_en': 'Gallon', 'name_es': 'Galón', 'tex': 'gal'},
        'litre': {'category': 'volume', 'name': 'Litre', 'name_pt': 'Litro', 'name_en': 'Litre', 'name_es': 'Litro', 'tex': 'l'},
        'militre': {'category': 'volume', 'name': 'Millilitre', 'name_pt': 'Mililitro', 'name_en': 'Millilitre', 'name_es': 'Mililitro', 'tex': 'ml'},
        'meter3': {'category': 'volume', 'name': 'Cubic Meter', 'name_pt': 'Metro Cúbico', 'name_en': 'Cubic Meter', 'name_es': 'Metro Cúbico', 'tex': 'm^3'},
        'mile3': {'category': 'volume', 'name': 'Cubic Mile', 'name_pt': 'Milha Cúbica', 'name_en': 'Cubic Mile', 'name_es': 'Milla Cúbica', 'tex': 'mi^3'},
        'foot3': {'category': 'volume', 'name': 'Cubic Foot', 'name_pt': 'Pé Cúbico', 'name_en': 'Cubic Foot', 'name_es': 'Pie Cúbico', 'tex': 'ft^3'},
        'inch3': {'category': 'volume', 'name': 'Cubic Inch', 'name_pt': 'Polegada Cúbica', 'name_en': 'Cubic Inch', 'name_es': 'Pulgada Cúbica', 'tex': 'in^3'},
        'barrel': {'category': 'volume', 'name': 'Barrel', 'name_pt': 'Barril', 'name_en': 'Barrel', 'name_es': 'Barril', 'tex': 'barrel'},
        'boe': {'category': 'volume', 'name': 'Barrel of Oil Equivalent', 'name_pt': 'Barril de Óleo Equivalente', 'name_en': 'Barrel of Oil Equivalent', 'name_es': 'Barril de Petróleo Equivalente', 'tex': 'barrel_e'},
        'toe': {'category': 'volume', 'name': 'Tonne of Oil Equivalent', 'name_pt': 'Tonelada de Óleo Equivalente', 'name_en': 'Tonne of Oil Equivalent', 'name_es': 'Tonelada de Petróleo Equivalente', 'tex': 'ton_e'},
        
        # Energy
        'watt': {'category': 'energy', 'name': 'Watt', 'name_pt': 'Watt', 'name_en': 'Watt', 'name_es': 'Vatio', 'tex': 'W'},
        'kilowatt': {'category': 'energy', 'name': 'Kilowatt', 'name_pt': 'Kilowatt', 'name_en': 'Kilowatt', 'name_es': 'Kilovatio', 'tex': 'kW'},
        'megawatt': {'category': 'energy', 'name': 'Megawatt', 'name_pt': 'Megawatt', 'name_en': 'Megawatt', 'name_es': 'Megavatio', 'tex': 'mW'},
        'gigawatt': {'category': 'energy', 'name': 'Gigawatt', 'name_pt': 'Gigawatt', 'name_en': 'Gigawatt', 'name_es': 'Gigavatio', 'tex': 'gW'},
        'terawatt': {'category': 'energy', 'name': 'Terawatt', 'name_pt': 'Terawatt', 'name_en': 'Terawatt', 'name_es': 'Teravatio', 'tex': 'tW'},
        'volt': {'category': 'energy', 'name': 'Volt', 'name_pt': 'Volt', 'name_en': 'Volt', 'name_es': 'Voltio', 'tex': 'V'},
        'kilovolt': {'category': 'energy', 'name': 'Kilovolt', 'name_pt': 'Kilovolt', 'name_en': 'Kilovolt', 'name_es': 'Kilovoltio', 'tex': 'kV'},
        'megavolt': {'category': 'energy', 'name': 'Megavolt', 'name_pt': 'Megavolt', 'name_en': 'Megavolt', 'name_es': 'Megavoltio', 'tex': 'mV'},
        'gigavolt': {'category': 'energy', 'name': 'Gigavolt', 'name_pt': 'Gigavolt', 'name_en': 'Gigavolt', 'name_es': 'Gigavoltio', 'tex': 'gV'},
        'teravolt': {'category': 'energy', 'name': 'Teravolt', 'name_pt': 'Teravolt', 'name_en': 'Teravolt', 'name_es': 'Teravoltio', 'tex': 'tV'},
        
        # People
        'person': {'category': 'people', 'name': 'Person', 'name_pt': 'Pessoa', 'name_en': 'Person', 'name_es': 'Persona', 'tex': 'per'},
        'household': {'category': 'people', 'name': 'Household', 'name_pt': 'Domicílio', 'name_en': 'Household', 'name_es': 'Hogar', 'tex': 'dom'},
        
        # Currency
        'ars': {'category': 'currency', 'name': 'Argentine Peso', 'name_pt': 'Peso Argentino', 'name_en': 'Argentine Peso', 'name_es': 'Peso Argentino', 'tex': 'ARS'},
        'brl': {'category': 'currency', 'name': 'Brazilian Real', 'name_pt': 'Real', 'name_en': 'Brazilian Real', 'name_es': 'Real Brasileño', 'tex': 'BRL'},
        'cad': {'category': 'currency', 'name': 'Canadian Dollar', 'name_pt': 'Dólar Canadense', 'name_en': 'Canadian Dollar', 'name_es': 'Dólar Canadiense', 'tex': 'CAD'},
        'clp': {'category': 'currency', 'name': 'Chilean Peso', 'name_pt': 'Peso Chileno', 'name_en': 'Chilean Peso', 'name_es': 'Peso Chileno', 'tex': 'CLP'},
        'usd': {'category': 'currency', 'name': 'US Dollar', 'name_pt': 'Dólar Americano', 'name_en': 'US Dollar', 'name_es': 'Dólar Estadounidense', 'tex': 'USD'},
        'eur': {'category': 'currency', 'name': 'Euro', 'name_pt': 'Euro', 'name_en': 'Euro', 'name_es': 'Euro', 'tex': 'EUR'},
        'gbp': {'category': 'currency', 'name': 'British Pound', 'name_pt': 'Libra Esterlina', 'name_en': 'British Pound', 'name_es': 'Libra Esterlina', 'tex': 'GBP'},
        'cny': {'category': 'currency', 'name': 'Chinese Yuan', 'name_pt': 'Yuan Chinês', 'name_en': 'Chinese Yuan', 'name_es': 'Yuan Chino', 'tex': 'CNY'},
        'inr': {'category': 'currency', 'name': 'Indian Rupee', 'name_pt': 'Rupia Indiana', 'name_en': 'Indian Rupee', 'name_es': 'Rupia India', 'tex': 'INR'},
        'jpy': {'category': 'currency', 'name': 'Japanese Yen', 'name_pt': 'Iene Japonês', 'name_en': 'Japanese Yen', 'name_es': 'Yen Japonés', 'tex': 'JPY'},
        'zar': {'category': 'currency', 'name': 'South African Rand', 'name_pt': 'Rand Sul-Africano', 'name_en': 'South African Rand', 'name_es': 'Rand Sudafricano', 'tex': 'ZAR'},
        
        # Economics
        'minimum_wage': {'category': 'economics', 'name': 'Minimum Wage', 'name_pt': 'Salário Mínimo', 'name_en': 'Minimum Wage', 'name_es': 'Salario Mínimo', 'tex': 'sm'},
        
        # Date-time
        'year': {'category': 'datetime', 'name': 'Year', 'name_pt': 'Ano', 'name_en': 'Year', 'name_es': 'Año', 'tex': 'y'},
        'semester': {'category': 'datetime', 'name': 'Semester', 'name_pt': 'Semestre', 'name_en': 'Semester', 'name_es': 'Semestre', 'tex': 'sem'},
        'quarter': {'category': 'datetime', 'name': 'Quarter', 'name_pt': 'Trimestre', 'name_en': 'Quarter', 'name_es': 'Trimestre', 'tex': 'q'},
        'bimester': {'category': 'datetime', 'name': 'Bimester', 'name_pt': 'Bimestre', 'name_en': 'Bimester', 'name_es': 'Bimestre', 'tex': 'bim'},
        'month': {'category': 'datetime', 'name': 'Month', 'name_pt': 'Mês', 'name_en': 'Month', 'name_es': 'Mes', 'tex': 'm'},
        'week': {'category': 'datetime', 'name': 'Week', 'name_pt': 'Semana', 'name_en': 'Week', 'name_es': 'Semana', 'tex': 'w'},
        'day': {'category': 'datetime', 'name': 'Day', 'name_pt': 'Dia', 'name_en': 'Day', 'name_es': 'Día', 'tex': 'd'},
        'hour': {'category': 'datetime', 'name': 'Hour', 'name_pt': 'Hora', 'name_en': 'Hour', 'name_es': 'Hora', 'tex': 'h'},
        'minute': {'category': 'datetime', 'name': 'Minute', 'name_pt': 'Minuto', 'name_en': 'Minute', 'name_es': 'Minuto', 'tex': 'min'},
        'second': {'category': 'datetime', 'name': 'Second', 'name_pt': 'Segundo', 'name_en': 'Second', 'name_es': 'Segundo', 'tex': 's'},
        
        # Percentage
        'percent': {'category': 'percentage', 'name': 'Percentage', 'name_pt': 'Porcentagem', 'name_en': 'Percentage', 'name_es': 'Porcentaje', 'tex': '%'},
    }
    
    for slug, unit_data in units.items():
        MeasurementUnit.objects.create(
            slug=slug,
            name=unit_data['name'],
            name_pt=unit_data['name_pt'],
            name_en=unit_data['name_en'],
            name_es=unit_data['name_es'],
            tex=unit_data['tex'],
            category=category_objects[unit_data['category']]
        )

def reverse_categories_and_units(apps, schema_editor):
    MeasurementUnitCategory = apps.get_model('v1', 'MeasurementUnitCategory')
    MeasurementUnit = apps.get_model('v1', 'MeasurementUnit')
    
    MeasurementUnit.objects.all().delete()
    MeasurementUnitCategory.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('v1', '0044_measurementunitcategory_measurementunit_tex_and_more'),
    ]

    operations = [
        migrations.RunPython(
            create_categories_and_units,
            reverse_categories_and_units
        ),
    ] 