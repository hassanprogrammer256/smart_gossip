from django.db import models

class Room(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'Rooms'
    
class Message(models.Model):
    room = models.ForeignKey(Room,on_delete=models.CASCADE)
    sender=models.CharField(max_length=255)
    message=models.TextField()

    def __str__(self):
        return self.room
    
    class Meta:
        db_table = 'Messages'
