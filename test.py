flag=0
with open("audio_flag.txt","r+") as f:
    a=int(f.read())
    if(a==0):
        flag=1
if(flag==1):
    with open("audio_flag.txt","w") as f:
        f.write("1")
print(a)