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

from .models import School, SchoolNote
from .forms import SchoolContactForm, SchoolNoteForm


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
    
    # Get air quality reading
    current_reading = school.get_current_reading()
    threshold_status = school.get_threshold_status()
    
    # Get notes for this school
    notes = school.notes.all()
    
    context = {
        'school': school,
        'current_reading': current_reading,
        'threshold_status': threshold_status,
        'notes': notes,
    }
    return render(request, 'schools/school_detail.html', context)


@login_required
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

