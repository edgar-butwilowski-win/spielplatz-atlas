import uuid
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from .geo_constants import LV95_SRID

class Playground(models.Model):
    organization=models.ForeignKey('tenants.Organization',on_delete=models.CASCADE,related_name='playgrounds')
    uuid=models.UUIDField(default=uuid.uuid4,unique=True)
    name=models.CharField(max_length=200)
    slug=models.SlugField(max_length=100)
    number=models.IntegerField(null=True,blank=True)
    address=models.CharField(max_length=300,blank=True)
    street_name=models.CharField(max_length=200,blank=True)
    house_number=models.CharField(max_length=40,blank=True)
    district=models.CharField(max_length=100,blank=True)
    latitude=models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True)
    longitude=models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True)
    location=gis_models.PointField(srid=LV95_SRID,null=True,blank=True)
    description=models.TextField(blank=True)
    construction_costs=models.FloatField(null=True,blank=True)
    inspection_suspended_from=models.DateField(null=True,blank=True)
    inspection_suspended_until=models.DateField(null=True,blank=True)
    default_visual_inspector=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='default_visual_playgrounds')
    default_operational_inspector=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='default_operational_playgrounds')
    default_annual_inspector=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='default_annual_playgrounds')
    photo=models.ForeignKey('media_assets.ImageAsset',on_delete=models.SET_NULL,null=True,blank=True,related_name='playgrounds')
    is_active=models.BooleanField(default=True)
    public_visible=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together=[('organization','slug')]
        ordering=['organization__name','name']
    def __str__(self): return f'{self.name} - {self.organization.name}'
    def clean(self):
        super().clean()
        if self.inspection_suspended_from and self.inspection_suspended_until and self.inspection_suspended_until<self.inspection_suspended_from: raise ValidationError({'inspection_suspended_until':'End date before start date.'})
        if bool(self.longitude)!=bool(self.latitude): raise ValidationError('Complete LV95 coordinate pair required.')
        for fn in ('default_visual_inspector','default_operational_inspector','default_annual_inspector'):
            inspector=getattr(self,fn)
            if inspector is None or inspector.is_superuser: continue
            profile=getattr(inspector,'profile',None)
            if not profile or profile.organization_id!=self.organization_id or not profile.may_inspect: raise ValidationError({fn:'Invalid inspector for organization.'})
    def sync_location_from_lv95(self): self.location=Point(float(self.longitude),float(self.latitude),srid=LV95_SRID) if self.longitude is not None and self.latitude is not None else None
    def save(self,*args,**kwargs): self.sync_location_from_lv95(); super().save(*args,**kwargs)
    @property
    def is_inspection_suspended(self):
        today=timezone.localdate()
        return bool(self.inspection_suspended_from and self.inspection_suspended_from<=today and (self.inspection_suspended_until is None or today<=self.inspection_suspended_until))
    @property
    def lv95_x(self): return self.longitude
    @property
    def lv95_y(self): return self.latitude
    def get_preview_photo(self):
        if self.photo_id: return self.photo
        obj=self.equipment.filter(is_active=True,public_visible=True,photo__isnull=False).select_related('photo').order_by('name').first()
        return obj.photo if obj else None
    def get_default_inspector_for_inspection_type(self,inspection_type): return {'visual':self.default_visual_inspector,'operational':self.default_operational_inspector,'annual':self.default_annual_inspector}.get(inspection_type)

class EquipmentType(models.Model):
    organization=models.ForeignKey('tenants.Organization',on_delete=models.CASCADE,related_name='equipment_types',null=True,blank=True)
    name=models.CharField(max_length=200)
    code=models.CharField(max_length=80,blank=True)
    norm_reference=models.CharField(max_length=200,blank=True)
    is_standard=models.BooleanField(default=False)
    standard_version=models.CharField(max_length=80,blank=True)
    source_note=models.TextField(blank=True)
    is_locked=models.BooleanField(default=False)
    is_active=models.BooleanField(default=True)
    class Meta: ordering=['name']
    def __str__(self): return f'{self.name} (Standard)' if self.is_standard else self.name

class EquipmentSupplier(models.Model):
    organization=models.ForeignKey('tenants.Organization',on_delete=models.CASCADE,related_name='equipment_suppliers',null=True,blank=True)
    name=models.CharField(max_length=200)
    tel_nr=models.CharField(max_length=80,blank=True)
    strasse=models.CharField(max_length=80,blank=True)
    plz_ort=models.CharField(max_length=80,blank=True)
    e_mail=models.EmailField(max_length=80,blank=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['name']
        unique_together=[('organization','name')]
    def __str__(self): return f'{self.name} - {self.organization.name}' if self.organization_id else f'{self.name} (global)'

class PlayEquipment(models.Model):
    playground=models.ForeignKey(Playground,on_delete=models.CASCADE,related_name='equipment')
    equipment_type=models.ForeignKey(EquipmentType,on_delete=models.PROTECT,related_name='equipment')
    name=models.CharField(max_length=200)
    sequence_number=models.PositiveIntegerField(null=True,blank=True)
    inventory_number=models.CharField(max_length=100,blank=True)
    supplier=models.ForeignKey(EquipmentSupplier,on_delete=models.SET_NULL,related_name='equipment',null=True,blank=True)
    norm=models.CharField(max_length=200,blank=True)
    year_built=models.DateField(null=True,blank=True)
    build_date=models.DateField(null=True,blank=True)
    demolition_date=models.DateField(null=True,blank=True)
    not_to_inspect=models.BooleanField(default=False)
    not_to_inspect_reason=models.CharField(max_length=500,blank=True)
    not_inspectable=models.BooleanField(default=False)
    not_inspectable_reason=models.CharField(max_length=500,blank=True)
    latitude=models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True)
    longitude=models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True)
    location=gis_models.PointField(srid=LV95_SRID,null=True,blank=True)
    public_visible=models.BooleanField(default=True)
    is_active=models.BooleanField(default=True)
    photo=models.ForeignKey('media_assets.ImageAsset',on_delete=models.SET_NULL,null=True,blank=True,related_name='play_equipment')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['playground__name','sequence_number','name']
    def __str__(self): return f'{self.name} - {self.playground.name}'
    def clean(self):
        super().clean()
        if self.not_to_inspect and not self.not_to_inspect_reason: raise ValidationError({'not_to_inspect_reason':'Reason required.'})
        if self.not_inspectable and not self.not_inspectable_reason: raise ValidationError({'not_inspectable_reason':'Reason required.'})
        if bool(self.longitude)!=bool(self.latitude): raise ValidationError('Complete LV95 coordinate pair required.')
    def sync_location_from_lv95(self): self.location=Point(float(self.longitude),float(self.latitude),srid=LV95_SRID) if self.longitude is not None and self.latitude is not None else None
    def save(self,*args,**kwargs): self.sync_location_from_lv95(); super().save(*args,**kwargs)
    def get_active_renovation_work_order(self):
        if hasattr(self,'active_renovation_work_order'): return self.active_renovation_work_order
        from inspections.work_orders import WorkOrder
        return WorkOrder.objects.filter(equipment=self,order_type=WorkOrder.TYPE_RENOVATION).exclude(status__in=[WorkOrder.STATUS_DONE,WorkOrder.STATUS_CANCELLED]).order_by('renovation_year','due_date','planned_date','created_at').first()
    @property
    def has_pending_renovation(self): return self.get_active_renovation_work_order() is not None
    @property
    def is_planned(self): return bool(self.year_built and self.year_built>timezone.localdate())
    @property
    def has_future_demolition(self): return bool(self.demolition_date and self.demolition_date>timezone.localdate())

class PlaygroundSurface(models.Model):
    SURFACE_TYPE_CHOICES=[('sand','Sand'),('gravel','Rundkies / Fallschutzkies'),('wood_chips','Holzschnitzel'),('bark','Rindenmulch'),('rubber','Fallschutzbelag'),('grass','Rasen'),('other','Sonstiger Belag')]
    playground=models.ForeignKey(Playground,on_delete=models.CASCADE,related_name='surfaces')
    name=models.CharField(max_length=200)
    surface_type=models.CharField(max_length=50,choices=SURFACE_TYPE_CHOICES,default='other')
    description=models.TextField(blank=True)
    public_visible=models.BooleanField(default=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['playground__name','name']
    def __str__(self): return f'{self.name} - {self.playground.name}'

class PlaygroundAccessory(models.Model):
    ACCESSORY_TYPE_CHOICES=[('bench','Sitzbank'),('waste_bin','Abfalleimer'),('fence','Zaun'),('gate','Tor'),('sign','Beschilderung'),('lighting','Beleuchtung'),('table','Tisch'),('shade','Sonnenschutz'),('other','Sonstige Ausstattung')]
    playground=models.ForeignKey(Playground,on_delete=models.CASCADE,related_name='accessories')
    name=models.CharField(max_length=200)
    accessory_type=models.CharField(max_length=50,choices=ACCESSORY_TYPE_CHOICES,default='other')
    description=models.TextField(blank=True)
    public_visible=models.BooleanField(default=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['playground__name','name']
    def __str__(self): return f'{self.name} - {self.playground.name}'

from .document_models import PlaygroundDocument
from .quartier_models import Quartier, QuartierImport
