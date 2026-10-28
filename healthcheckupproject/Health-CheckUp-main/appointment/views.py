import uuid
from django.shortcuts import render, redirect
from django.http import HttpResponse
from appointment.forms import NewUserForm, LoginForm
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.views.generic import TemplateView, ListView
from appointment.models import Doctor, Timeslots, Appointment

def register_request(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Health Checkup, {user.username}! Your account has been registered successfully.")
            return redirect('/')
        else:
            messages.error(request, "Registration could not be completed. Please review the highlighted errors.")
    else:
        form = NewUserForm()

    return render(request=request, template_name="appointment/register.html", context={"register_form": form})


def login_request(request):
    if request.user.is_authenticated:
        return redirect('/')

    redirect_to = request.POST.get('next') or request.GET.get('next') or '/'

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect(redirect_to)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(
        request=request,
        template_name="appointment/login.html",
        context={"login_form": form, "next": redirect_to}
    )



def search(request):
    if request.method == 'POST':
        timeslot = request.POST.get('timeSlot')
        doctorName = request.POST.get('doctorName')

        if not timeslot or not doctorName:
            return HttpResponse("Missing booking details.", status=400)

        doc = Doctor.objects.filter(name=doctorName).first()
        if doc is None:
            return HttpResponse("Selected doctor could not be found.", status=404)

        docEmail = doc.email
        current_user = request.user
        userMail = current_user.email

        # Create the booking: a fresh timeslot for this doctor plus an
        # Appointment record with a freshly generated video call id.
        # (Previously this looked up doc.appointment_set.all()[0], which
        # assumed a booking already existed and raised IndexError for
        # every doctor that had never been booked before.)
        slot = Timeslots.objects.create(doctor=doc)
        meeting_id = uuid.uuid4().hex[:12]
        appointment = Appointment.objects.create(
            user=current_user,
            meetingId=meeting_id,
            doctor=doc,
            slot=slot,
        )

        subject = 'Request for Appointment'
        message = (
            f'Patient Name: {current_user.username} \n'
            f'Patient Email Id: {userMail} \n'
            f'Doctor Name: {doctorName} \n'
            f'Doctor Mail Id: {docEmail} \n'
            f'Time slot {timeslot} \n'
            f'Meeting Id for video call: {appointment.meetingId}'
        )
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [docEmail, userMail]
        try:
            status = send_mail(subject, message, from_email, recipient_list)
        except Exception:
            status = 0
        if status == 1:
            return HttpResponse("done")
        else:
            return HttpResponse("")

    doctors = Doctor.objects.all()[:5]
    context = {
        "doctors": doctors
    }
    return render(request, 'videocall/videocallpage.html', context)


class BookAppointment(ListView):
    model = Doctor
    template_name = 'videocall/output.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        state = self.request.GET.get('state', '')
        specialization = self.request.GET.get('specialization', '')
        return self.model.objects.filter(
            state__contains=state,
            specialization__contains=specialization,
        )


def logout_request(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect("/login/")

