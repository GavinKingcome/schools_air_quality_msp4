"""
schools/views.py

Views for school listing, detail, editing, and note management.
Provides full CRUD functionality:
  - Create: Add notes about a school
  - Read: View school list and detail pages
  - Update: Edit school contact information and notes
  - Delete: Remove notes
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db import models  # needed for Q lookups in search
from subscriptions.decorators import subscription_required

from django.utils import timezone

from .models import School, SchoolNote
from .forms import SchoolContactForm, SchoolNoteForm


# Shown in this order on the school page
POLLUTANTS = [('no2', 'NO₂'), ('pm25', 'PM2.5'), ('pm10', 'PM10')]

CONFIDENCE_LABELS = {
    'high': 'High', 'medium-high': 'Medium-high', 'medium': 'Medium',
    'medium-low': 'Medium-low', 'low': 'Low',
}


def describe_vs_average(factor):
    """
    compared_with_usual in plain words, matching the map popup.
    e.g. 0.7 -> '30% below its yearly average'
    """
    if factor is None:
        return 'no yearly average to compare with yet'
    if factor < 0.2 or factor > 5:
        return 'far from its yearly average: may be a sensor fault'
    if factor >= 2:
        return f'about {factor:.1f} times its yearly average'
    pct = round((factor - 1) * 100)
    if abs(pct) < 5:
        return 'about its yearly average'
    return f'{pct}% above its yearly average' if pct > 0 else f'{-pct}% below its yearly average'


def describe_age(timestamp):
    """
    When the reading was taken, in plain words, and whether it's old.
    e.g. ('Reading at 14:00 today (2 hours ago).', False)
    """
    if not timestamp:
        return None, False
    local = timezone.localtime(timestamp)
    now = timezone.localtime()
    hours = int((now - local).total_seconds() // 3600)
    day = 'today' if local.date() == now.date() else f'{local:%A} {local.day} {local:%b}'
    if hours < 1:
        ago = 'less than an hour ago'
    elif hours == 1:
        ago = '1 hour ago'
    else:
        ago = f'{hours} hours ago'
    return f'Reading at {local:%H:%M} {day} ({ago}).', hours >= 6


def format_distance(metres):
    """e.g. 368 -> '368 m', 1820 -> '1.8 km'"""
    if metres is None:
        return ''
    return f'{round(metres)} m' if metres < 1000 else f'{metres / 1000:.1f} km'

def schools_list(request):
    """List all schools with search and filter functionality."""
    schools = School.objects.all().order_by('name')
    
    # Search by name or postcode
    query = request.GET.get('q', '').strip()
    if query:
        schools = schools.filter(
            models.Q(name__icontains=query) |
            models.Q(postcode__icontains=query)
        )
    
    # Filter by borough
    borough = request.GET.get('borough', '').strip()
    if borough:
        schools = schools.filter(borough__iexact=borough)
    
    # Filter by school type
    school_type = request.GET.get('type', '').strip()
    if school_type:
        schools = schools.filter(school_type=school_type)
    
    # Add current reading method to each school for accurate badge display
    schools_with_method = []
    for school in schools:
        current_reading = school.get_current_reading()
        method = current_reading.get('method', '')
        
        # Map method to data_source for display consistency with map
        if method == 'direct':
            actual_data_source = 'DIRECT'
        elif method == 'laei_adjusted':
            actual_data_source = 'ADJUSTED'
        else:  # laei_only or empty
            actual_data_source = 'LAEI_ONLY'
        
        school.actual_data_source = actual_data_source
        schools_with_method.append(school)
    
    context = {
        'schools': schools_with_method,
        'query': query,
        'borough': borough,
        'school_type': school_type,
        'school_count': len(schools_with_method),
    }
    return render(request, 'schools/schools_list.html', context)


def school_detail(request, pk):
    """Display detailed information about a single school."""
    school = get_object_or_404(School, pk=pk)

    current_reading = school.get_current_reading()
    threshold_status = school.get_threshold_status()

    # Latest reading: one row per pollutant, compared with the sensor's yearly average
    latest_rows = []
    if current_reading.get('method') in ('direct', 'laei_adjusted'):
        compared = current_reading.get('compared_with_usual', {})
        unadjusted = current_reading.get('unadjusted', [])
        for key, name in POLLUTANTS:
            value = current_reading.get(key)
            if value is None or key in unadjusted:
                latest_rows.append({'name': name, 'value': None,
                                    'text': 'no current reading from this sensor'})
            else:
                latest_rows.append({'name': name, 'value': value,
                                    'text': describe_vs_average(compared.get(key))})

    # The adjusted method keeps its reading time inside adjustment_factors
    timestamp = (current_reading.get('reading_timestamp')
                 or current_reading.get('adjustment_factors', {}).get('reading_timestamp'))
    reading_age, reading_is_old = describe_age(timestamp)

    # Why there's no latest reading, if there isn't one
    if school.direct_sensor or school.reference_sensor:
        no_reading_reason = 'Its sensor has sent no reading in the last 48 hours.'
    else:
        no_reading_reason = "There's no sensor within 2 km."

    # Typical year: one row per pollutant, in the same order
    typical_rows = [
        {'name': name, **threshold_status[key]}
        for key, name in POLLUTANTS if key in threshold_status
    ]

    notes = school.notes.all()

    context = {
        'school': school,
        'current_reading': current_reading,
        'latest_rows': latest_rows,
        'reading_age': reading_age,
        'reading_is_old': reading_is_old,
        'sensor_distance_text': format_distance(current_reading.get('sensor_distance')),
        'confidence_label': CONFIDENCE_LABELS.get(current_reading.get('confidence'), ''),
        'no_reading_reason': no_reading_reason,
        'typical_rows': typical_rows,
        'notes': notes,
    }
    return render(request, 'schools/school_detail.html', context)


@login_required
@subscription_required
def school_edit(request, pk):
    """
    Edit school contact information.
    Only staff users or the school's associated users can edit.
    """
    school = get_object_or_404(School, pk=pk)
    
    # Permission check: only staff can edit school details
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit school details.')
        return redirect('schools:school_detail', pk=pk)
    
    if request.method == 'POST':
        form = SchoolContactForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, f'{school.name} contact details updated successfully.')
            return redirect('schools:school_detail', pk=pk)
    else:
        form = SchoolContactForm(instance=school)
    
    context = {
        'form': form,
        'school': school,
    }
    return render(request, 'schools/school_edit.html', context)


@login_required
def note_create(request, school_pk):
    """Create a new note for a school."""
    school = get_object_or_404(School, pk=school_pk)
    
    if request.method == 'POST':
        form = SchoolNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.school = school
            note.author = request.user
            note.save()
            messages.success(request, 'Your note has been added successfully.')
            return redirect('schools:school_detail', pk=school_pk)
    else:
        form = SchoolNoteForm()
    
    context = {
        'form': form,
        'school': school,
    }
    return render(request, 'schools/note_form.html', context)


@login_required
def note_edit(request, pk):
    """Edit an existing note. Only the author can edit their note."""
    note = get_object_or_404(SchoolNote, pk=pk)
    
    # Permission check: only the author can edit
    if note.author != request.user:
        messages.error(request, 'You can only edit your own notes.')
        return redirect('schools:school_detail', pk=note.school.pk)
    
    if request.method == 'POST':
        form = SchoolNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your note has been updated.')
            return redirect('schools:school_detail', pk=note.school.pk)
    else:
        form = SchoolNoteForm(instance=note)
    
    context = {
        'form': form,
        'school': note.school,
        'note': note,
    }
    return render(request, 'schools/note_form.html', context)


@login_required
def note_delete(request, pk):
    """Delete a note. Only the author can delete their note."""
    note = get_object_or_404(SchoolNote, pk=pk)
    
    # Permission check: only the author can delete
    if note.author != request.user:
        messages.error(request, 'You can only delete your own notes.')
        return redirect('schools:school_detail', pk=note.school.pk)
    
    if request.method == 'POST':
        school_pk = note.school.pk
        note.delete()
        messages.success(request, 'Your note has been deleted.')
        return redirect('schools:school_detail', pk=school_pk)
    
    context = {
        'note': note,
        'school': note.school,
    }
    return render(request, 'schools/note_confirm_delete.html', context)

