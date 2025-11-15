
from django.http import request
from django.shortcuts import render, redirect           

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .forms import RegisterForm
# Create your views here.

def index(request):
    data = {
        'title': 'Main page',
    }
    return render(request, 'main/index.html', data)

def about(request):
    return render(request, 'main/about.html')



def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()  
            return redirect('login')  
    else:
        form = RegisterForm()
    return render(request, 'main/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        if user is not None:
            user = authenticate(username=user.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  

    
        return render(request, 'main/login.html', {
            'error': 'Incorrect email or password'
        })

    return render(request, 'main/login.html')
    

def logout_view(request):
    logout(request)
    return redirect('home')