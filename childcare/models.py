from django.db import models

# Create your models here.
class ChildcareSetting(models.Model):
    """An Ofsted-registered early-years childcare provider.

    Imported from the schools-pollution-analysis pipeline
    (southwark_lambeth_childcare.csv). Home-based providers
    (childminders, domestic premises) arrive with name, address and
    coordinates withheld by Ofsted: they are kept for counts and
    aggregate analysis but cannot be mapped.
    """

    PROVIDER_TYPE_CHOICES = [
        ('non_domestic', 'Childcare on non-domestic premises'),
        ('childminder', 'Childminder'),
        ('domestic', 'Childcare on domestic premises'),
    ]

    # Identity. URN is the stable Ofsted key - imports match on it.
    urn = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255, blank=True,
                            help_text='Blank for home-based providers (withheld by Ofsted)')
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPE_CHOICES)
    register_combination = models.CharField(max_length=20, blank=True,
                                            help_text='EYR only / EYR-CCR / ALL')
    places = models.IntegerField(null=True, blank=True)

    # Location. Null for home-based providers.
    postcode = models.CharField(max_length=10, blank=True)
    borough = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    easting = models.IntegerField(null=True, blank=True)
    northing = models.IntegerField(null=True, blank=True)
    lsoa21 = models.CharField(max_length=12, blank=True,
                              help_text='2021-boundary LSOA code, for IMD/IDACI joins')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['provider_type','name']

    def __str__(self):
        return self.name or f'Home-based provider {self.urn}'

    @property
    def is_mappable(self) -> bool:
        return self.latitude is not None and self.longitude is not None
