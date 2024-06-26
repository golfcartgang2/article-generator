from unittest import result
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.permissions import  AllowAny
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
from pytube import YouTube
import os
import assemblyai as aai
import openai
from .models import BlogPost
import requests 
import time

# Create your views here.
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        
        #get yt title
        title = yt_title(yt_link)

        #get transcript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': "Failed to get transcript"}, status=500)


        # use openAI to generate the blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to generate blog article"}, status=500)

        # save blog article to database 
        new_blog_article = BlogPost.objects.create(
            user= request.user,
            youtube_title = title, 
            youtube_link =yt_link,
            generated_content =blog_content
        )
        new_blog_article.save()

        # return blog article as response 
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status = 405)

def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio(link):
    yt =  YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path = settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = "58c2815cb88c48649faeeb60e2d3c636" 

    transcriber = aai.Transcriber()

    audio_url = "https://storage.googleapis.com/aai-web-samples/5_common_sports_injuries.mp3"

    transcript = transcriber.transcribe(audio_url)

    prompt = "Provide a brief summary of the transcript."

    result = transcript.lemur.task(prompt)

    print(result.response)

    polling_endpoint = "https://api.assemblyai.com/v2/transcript/" + transcript.id
    headers = {"Authorization": "Bearer 58c2815cb88c48649faeeb60e2d3c636"}

    while True:
        transcription_result = requests.get(polling_endpoint, headers=headers).json()
        config = aai.TranscriptionConfig(speaker_labels=True)

        transcript = transcriber.transcribe(audio_file, config)

        print(transcript.text)
        for utterance in transcript.utterances:
            print(f"Speaker {utterance.speaker}: {utterance.text}")

        if transcription_result['status'] == 'completed':
            return transcription_result['text']
        elif transcription_result['status'] == 'error':
            raise RuntimeError(f"Transcription failed: {transcription_result['error']}")
        else:
            time.sleep(3)
    

def generate_blog_from_transcription(transcription):
        # generate blog content from transcription  
        openai.api_key = "sk-proj-ghqQP35DQpudGgsu4iXRT3BlbkFJqksdZTKD6PJ7zpBUOuBS"
        prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but don't make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"
        
        response = openai.Completion.create(
            engine="davinci",
            prompt=prompt,
            max_tokens=1000,
        )
        
        generated_content = response.choices[0].text.strip()
        
        return generated_content

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, " recents.html", {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user: 
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login (request, user)
            return redirect('/')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    return render(request, 'login.html')

def stay_logged_out(request):
    logout(request)
    return redirect(index)

def user_signup(request):
    if request.method == 'POST': 
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        retypepassword = request.POST['retypepassword']

        if password == retypepassword:
            # Create a new user
            new_user = User.objects.create_user(username, email, password)
            new_user.save()
            #Log the user in 
            user = authenticate(username=username, password=password,)
            if user is not None:
                login(request, user)
                return redirect('index') #Redirect to the index page
            
        else:
            # Passwords do not match
            error_message = "Password do not match"
            return render(request, 'signup.html', {'error_message': error_message})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

