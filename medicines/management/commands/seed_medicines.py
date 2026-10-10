# Django Management Command Imports

from django.core.management.base import BaseCommand


# Local Application Model Imports

from medicines.models import Medicine


# Medicine Dataset Seed Command

class Command(BaseCommand):
    """
    Management command for seeding the initial Indian
    essential medicines dataset into the database.
    """

    # Command Description

    help = 'Seeds initial Indian essential medicines dataset into the database.'

    # Command Execution

    def handle(self, *args, **options):
        """
        Seeds the predefined medicines dataset into the database.
        """

        # Initial Medicine Dataset

        medicines_data = [
            {'brand_name': 'Crocin', 'generic_name': 'Paracetamol', 'dosage_form': 'Tablet', 'strength': '500mg', 'manufacturer': 'GSK'},
            {'brand_name': 'Dolo-650', 'generic_name': 'Paracetamol', 'dosage_form': 'Tablet', 'strength': '650mg', 'manufacturer': 'Micro Labs'},
            {'brand_name': 'Augmentin 625', 'generic_name': 'Amoxicillin + Clavulanic Acid', 'dosage_form': 'Tablet', 'strength': '625mg', 'manufacturer': 'GSK'},
            {'brand_name': 'Azithral 500', 'generic_name': 'Azithromycin', 'dosage_form': 'Tablet', 'strength': '500mg', 'manufacturer': 'Alembic'},
            {'brand_name': 'Glycomet 500', 'generic_name': 'Metformin', 'dosage_form': 'Tablet', 'strength': '500mg', 'manufacturer': 'USV'},
            {'brand_name': 'Pan-40', 'generic_name': 'Pantoprazole', 'dosage_form': 'Tablet', 'strength': '40mg', 'manufacturer': 'Alkem'},
            {'brand_name': 'Pantocid 40', 'generic_name': 'Pantoprazole', 'dosage_form': 'Tablet', 'strength': '40mg', 'manufacturer': 'Sun Pharma'},
            {'brand_name': 'Telma 40', 'generic_name': 'Telmisartan', 'dosage_form': 'Tablet', 'strength': '40mg', 'manufacturer': 'Glenmark'},
            {'brand_name': 'Amlokind-5', 'generic_name': 'Amlodipine', 'dosage_form': 'Tablet', 'strength': '5mg', 'manufacturer': 'Mankind'},
            {'brand_name': 'Atorva 10', 'generic_name': 'Atorvastatin', 'dosage_form': 'Tablet', 'strength': '10mg', 'manufacturer': 'Zydus'},
            {'brand_name': 'Cetzine', 'generic_name': 'Cetirizine', 'dosage_form': 'Tablet', 'strength': '10mg', 'manufacturer': 'Dr Reddy'},
            {'brand_name': 'Brufen 400', 'generic_name': 'Ibuprofen', 'dosage_form': 'Tablet', 'strength': '400mg', 'manufacturer': 'Abbott'},
            {'brand_name': 'Combiflam', 'generic_name': 'Ibuprofen + Paracetamol', 'dosage_form': 'Tablet', 'strength': '400mg/325mg', 'manufacturer': 'Sanofi'},
            {'brand_name': 'Montair LC', 'generic_name': 'Montelukast + Levocetirizine', 'dosage_form': 'Tablet', 'strength': '10mg/5mg', 'manufacturer': 'Cipla'},
            {'brand_name': 'Asthalin Inhaler', 'generic_name': 'Salbutamol', 'dosage_form': 'Inhaler', 'strength': '100mcg', 'manufacturer': 'Cipla'},
            {'brand_name': 'Ascoril LS', 'generic_name': 'Levosalbutamol + Ambroxol + Guaiphenesin', 'dosage_form': 'Syrup', 'strength': '100ml', 'manufacturer': 'Glenmark'},
            {'brand_name': 'Oflox 200', 'generic_name': 'Ofloxacin', 'dosage_form': 'Tablet', 'strength': '200mg', 'manufacturer': 'Cipla'},
            {'brand_name': 'Ciplox 500', 'generic_name': 'Ciprofloxacin', 'dosage_form': 'Tablet', 'strength': '500mg', 'manufacturer': 'Cipla'},
            {'brand_name': 'Eldoper', 'generic_name': 'Loperamide', 'dosage_form': 'Capsule', 'strength': '2mg', 'manufacturer': 'Micro Labs'},
            {'brand_name': 'Digene', 'generic_name': 'Antacid', 'dosage_form': 'Syrup/Tablet', 'strength': '200ml', 'manufacturer': 'Abbott'},
        ]

        # Track Newly Created Medicine Records

        count = 0

        # Create Medicine Records

        for item in medicines_data:
            obj, created = Medicine.objects.get_or_create(
                brand_name=item['brand_name'],
                defaults=item
            )

            # Increment Created Medicine Counter

            if created:
                count += 1

        # Display Command Success Message

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {count} medicines into the database."
            )
        )