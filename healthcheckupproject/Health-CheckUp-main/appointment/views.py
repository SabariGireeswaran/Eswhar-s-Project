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
from appointment.models import Doctor, Appointment

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
		timeslot = request.POST['timeSlot']
		doctorName = request.POST['doctorName']
		doc = Doctor.objects.get(name = doctorName)
		docEmail = doc.email

		userName = request.user
		current_user = User.objects.get(username = userName)
		userMail = current_user.email

		meetId = doc.appointment_set.all()[0]

		subject = 'Request for Appointment'
		message = f'Patient Name: {userName} \nPatient Email Id: {userMail} \nDoctor Name: {doctorName} \nDoctor Mail Id: {docEmail} \nTime slot {timeslot} \nMeeting Id for video call: {meetId}' 
		from_email = settings.EMAIL_HOST_USER
		recipient_list = [docEmail , userMail]
		status = send_mail(subject, message, from_email, recipient_list)
		if status == 1:
			return HttpResponse("done")
		else:
			return HttpResponse("")

	doctors = Doctor.objects.all()[:5]
	context = {
        "doctors" : doctors
    }
	return render(request , 'videocall/videocallpage.html' , context)


class BookAppointment(ListView):
	model = Doctor
	template_name = 'videocall/output.html'
	context_object_name = 'appointment'
	
	def get_queryset(self):
		obj = self.model.objects.filter(state__contains=self.request.GET['state'], 
		specialization__contains=self.request.GET['specialization'])
		return obj


def logout_request(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect("/login/")

