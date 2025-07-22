from django.shortcuts import render,redirect
from .models import *

def CreateRoom(request):
    if request.method == "POST":
        user_name = request.POST['user_name']
        group_name = request.POST['group_name']
        try:
            get_group = Room.objects.get(name = group_name)
        except Room.DoesNotExist:
            new_group = Room(name=group_name)
            new_group.save()

        return redirect('group',group_name=group_name,user_name=user_name)

    return render(request,'index.html')

def MessageView(request,group_name,user_name):
    get_room = Room.objects.get(name=group_name)
    get_message = Message.objects.get(room=get_room)

    context = {
        "user":user_name,
        "group":get_room,
        "messages":get_message
    }
    return render(request,'_message.html',context)