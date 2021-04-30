#!/usr/bin/env python3
import boto3				#importing boto3 from aws
from operator import itemgetter         #this allows me to iterate through items
import subprocess
import time
from datetime import datetime, timedelta
cloudwatch = boto3.resource('cloudwatch')       #we will use cloudwatch for the metrics

client = boto3.client('ec2')            #creating a client off ec2
response = client.describe_images(      #describing the images associated with Amazon Linux 2
    Filters=[
        {
            'Name': 'description',      #The filter that will filter down through the AMI's to what i require
            'Values': [
                'Amazon Linux 2 AMI*',
            ]
        },
    ],
    Owners=[
        'amazon'
    ]
)
                                        # Sort on Creation date Descending to retrieve the newest and up todate AMI
image_details = sorted(response['Images'],key=itemgetter('CreationDate'),reverse=True)
ami_id = image_details[0]['ImageId']    #The AMI at position 0, the newest id available from Amazon
print (ami_id)

ec2 = boto3.resource('ec2')            #creating an instance of ec2                 #creating a key pair to be used in the instance
key_nam = ""
while key_nam is "":                                   #this is a while loop where it will keep looping till user inputs
    key_nam = input("Please enter your KeyName: ")     #This is where the name of the key will be stored in variable

new_keypair = key_nam + ".pem"                        #adding on the .pem for the user so everything will run smoothly
                                                      # create a file to store the key locally
outfile = open(new_keypair,'w')
                                                      # call the boto ec2 function to create a key pair
key_pair = ec2.create_key_pair(KeyName=key_nam)
                                                      # capture the key and store it in a file
KeyPairOut = str(key_pair.key_material)
                                                      # Noooow write the data from the key to the outfile
outfile.write(KeyPairOut)
outfile.close()                                       # Close the outfile, this is the only way it run correctly

cmds = 'chmod 400 ' + new_keypair                     # CReating a variable that will allow all the right permissions
success = subprocess.run(cmds, shell=True)            # This subprocess will run the command


try:
    instance = ec2.create_instances(       #now we create the instance with all diferent parameters
    ImageId=ami_id,                         #using the most up to date ami id
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',                 #creating a t2 nano
    KeyName=key_nam,                        #keyPair dynamically created by the user, the variable that stores it
    SecurityGroupIds=['sg-0a7ac7e5954813cfb'],   # Hard coded the security group
    TagSpecifications=[                          #crearing the tag for the instance
        {
            'ResourceType': 'instance',
            'Tags': [
                        {
                            'Key': 'name',
                            'Value': 'web server'
                        },
                    ]
         },
     ],                                        #The user data in a multi-string
     UserData="""#!/bin/bash
                  yum update -y
                  yum install httpd -y
                  systemctl enable httpd
                  systemctl start httpd""")


    print (instance[0].state)
except Exception as error:             #some exception handling diplaying the error if there is one
    print (error)

s3 = boto3.resource("s3")
                                            # Prompt the user to enter an Bucket Name and use it as a parameter
buc_nam = ""
while buc_nam is "":
    buc_nam = input("Please enter your BucketName: ")

buc_parm = buc_nam + "-" + time.strftime("%Y-%m-%d-%H-%M")      #This is adding on the date and time, so you can eneter a name and it will be uni$

cmd = "curl -O http://devops.witdemo.net/image.jpg"             #download the image.jpg localy so i can use the file
success = subprocess.run(cmd, shell=True)                       #subprocess to run the curl command and shell = true means run as a shell line
if success.returncode == 0:                                     #a little validation to let user know if it worked
    print ("Successfully executed")
try:                                            #A try block for exception handling
    response = s3.create_bucket(ACL='public-read', Bucket=buc_parm, CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})
    print (response)                             #The creation of a bucket using parameter that user entered earlier and making bucket
                                                #public read and creating location constraint
except Exception as error:                      #The error handling, that will throw the error
    print (error)
    exit()                                       # will print the error to the user and then exit
try:
    object_name = 'image.jpg'                    #This is the image we curl up above and now we are creating a variable name of it
    response = s3.Object(buc_parm, object_name).put(ACL='public-read', Body=open(object_name, 'rb'))
    print(response)                              #This is putting the image.jpg into the bucket and making it public read
except Exception as error:                      #Another exception handling
    print(error)

print("--------------------------------------------")
print("Just a moment as the instance is being setup")           #Just for the user to know what is happening in the script and where they stand
print("--------------------------------------------")

time.sleep(100)                                  #The programme sleeps for 80 seconds while the instance is being created externally
#instance[0].wait_until_running()
instance[0].reload()                            #always good to call reload when using an instance
ip_addr = instance[0].public_ip_address         #assigning the public ip address to a parameter

print("------------------------------------------------")
print("Just a moment as the ssh instance is being setup")       #For user to know where they stand with the programme
print("------------------------------------------------")

cmdbase = "ssh -o StrictHostKeyChecking=no -i " + key_nam +".pem ec2-user@" + ip_addr         #sshing into newly created instance
print (cmdbase)       # just for debugging

cmd1 = cmdbase +  " 'curl -O http://devops.witdemo.net/image.jpg'"                              #downloading image at this instance
print (cmd1)          # just for debugging
result = subprocess.run(cmd1, shell=True)                                                       #subprocess to run as i was using the command line
if result.returncode == 0:
    print ("Successfully executed")

cmd2 = cmdbase +  " 'chmod 774 image.jpg'"           #making the image to read only to public but granted all for the user and group
print (cmd2)          # just for debugging
result2 = subprocess.run(cmd2, shell=True)
if result2.returncode == 0:
    print ("Successfully executed")

cmd3 =  "echo '<img src=https://s3-eu-west-1.amazonaws.com/" + buc_parm + "/" + object_name + ">' >> index.html"
print (cmd3)         #This is the url for the image that takes the parameter passed in by the user and the image.jpg
result3 = subprocess.run(cmd3, shell=True)
if result3.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")                                             #A try block for exception handling

cmd4 = "echo '<br>Private IP address: <br>' >> index.html" #This is printing localy to index file
print(cmd4)
result4 = subprocess.run(cmd4, shell=True)
if result4.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")


cmd8 = "scp -i " + new_keypair + " index.html  ec2-user@" + ip_addr +":."      #This is copying the index.html file to my aws 
print (cmd8)
result8 = subprocess.run(cmd8, shell=True)
if result8.returncode == 0:
    print ("Successfully executed index sent")
    print ("--------------------------------")

cmd5 =cmdbase +  " 'curl --silent  http://169.254.169.254/latest/meta-data/public-ipv4 >> index.html'"  #this is collecting the ipv4 addrress and curl it to the index.html
print (cmd5)            #just for debugging
result5 = subprocess.run(cmd5, shell=True)      #a subprocess that executes the previous string constructed and execute$
if result5.returncode == 0:
    print ("Successfully executed the public-ipv4")             #just for debugging letting me know if its working
    print ("-------------------------------------")

cmd15 =cmdbase + " 'echo '" " ]___ ' >> index.html'"            #This is just some design to make the metadata more readable and user friendly
print(cmd15)
result15 = subprocess.run(cmd15, shell=True)
if result15.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")


cmd6 =cmdbase + " 'echo '"     " Availability Zone: ' >> index.html'"   #This is echoing a string Avaliability Zone: to index.html
print(cmd6)
result6 = subprocess.run(cmd6, shell=True)
if result6.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")

cmd14 =cmdbase + " 'echo '" " ___[ ' >> index.html'"           #yet again for more user friendly meta data to the eye
print(cmd14)
result14 = subprocess.run(cmd14, shell=True)
if result14.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")


cmd7 =cmdbase +  " 'curl --silent  http://169.254.169.254/latest/meta-data/placement/availability-zone >> index.html'" #collecting the availability zone and sending toindex.html
print (cmd7)            #just for debugging
result7 = subprocess.run(cmd7, shell=True)      #a subprocess that executes the command store in the variable
if result7.returncode == 0:
    print ("Successfully executed the availabilty-zone")             #just for debugging letting me know if its working
    print("-------------------------------------")

cmd13 =cmdbase + " 'echo '" "]___ ' >> index.html'"    #for design purposes, to make it look nice
print(cmd13)
result13 = subprocess.run(cmd13, shell=True)
if result13.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")


cmd10 =cmdbase + " 'echo '"     " Host Name: ' >> index.html'"   #echoing a string to index.html
print(cmd10)
result10 = subprocess.run(cmd10, shell=True)
if result10.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")

cmd12 =cmdbase + " 'echo '" " ___[ ' >> index.html'"          #for design purposes, better readability
print(cmd12)
result12 = subprocess.run(cmd12, shell=True)
if result12.returncode == 0:
    print ("Successfully executed")
    print("------------------------------------------")


cmd11 =cmdbase +  " 'curl --silent  http://169.254.169.254/latest/meta-data/public-hostname >> index.html'" 
print (cmd11)            #just for debugging
result11 = subprocess.run(cmd11, shell=True)      #a subprocess that executes the variable that holds the command stored in it
if result11.returncode == 0:
    print ("Successfully executed the Host name")             #just for debugging letting me know if its working
    print("-------------------------------------")


cmd9 = cmdbase +  " 'sudo cp index.html /var/www/html'"                 #THis is copying and replacing the apache index server file with the one created here
print (cmd9)          # just for debugging
result9 = subprocess.run(cmd9, shell=True)
if result9.returncode == 0:
    print ("Successfully executed")
    print("-----------------------------------")


cmd13 = "scp -i " + new_keypair + " monitor.sh  ec2-user@" + ip_addr +":."      #This is copying the index.html file to my aws 
print (cmd13)        #debugging purposes
result13 = subprocess.run(cmd13, shell=True)
if result13.returncode == 0:
    print ("Successfully executed")
    print("----------------------------------")

cmd14 = cmdbase + " 'chmod 700 monitor.sh'"                   #This is giving the correct permisions to the monitor script
print (cmd14)
result14 = subprocess.run(cmd14, shell=True)
if result14.returncode == 0:
    print ("Successfully executed")
    print("----------------------------------")               #Some User friendly step by step, to help user follow.

print ("*****Monitor Script loading...*****")
print("----------------------------------")

cmd15 = cmdbase + " './monitor.sh'"                           # runinng the monitor script
result15 = subprocess.run(cmd15, shell=True)

print("-------------------------------------------------")
print("Just a moment as the Cloud Metrics is being setup")              #For the user just to show programme status
print("-------------------------------------------------")

time.sleep(350)                                                         #nearly 6 minutes to allow instance to run long enough for metrics to be collected

instance[0].reload()                                                    # always good to reload a instance before accessing the instance

instid = instance[0].id                                                 #assiging the instance id to a variable

instances = ec2.Instance(instid)
print (instances)
instances.monitor()       # Enables detailed monitoring on instance 

metric_iterator = cloudwatch.metrics.filter(Namespace='AWS/EC2',
                                            MetricName='CPUUtilization',                #collecting data from the cpuUtilization
                                            Dimensions=[{'Name':'InstanceId', 'Value': instid}])

metric = list(metric_iterator)[0]    # extract first (only) element

responses = metric.get_statistics(StartTime = datetime.utcnow() - timedelta(minutes=5),   # 5 minutes ago
                                 EndTime=datetime.utcnow(),                              # now
                                 Period=300,                                             # 5 min intervals
                                 Statistics=['Average'])

metric_iterators = cloudwatch.metrics.filter(Namespace='AWS/EC2',
                                            MetricName='NetworkOut',                    #collecting data from the networkOut
                                            Dimensions=[{'Name':'InstanceId', 'Value': instid}])

metrics = list(metric_iterators)[0]    # extract first (only) element

res = metrics.get_statistics(StartTime = datetime.utcnow() - timedelta(minutes=5),   # 5 minutes ago
                                 EndTime=datetime.utcnow(),                              # now
                                 Period=300,                                             # 5 min intervals
                                 Statistics=['Average'])

print(" ")
print(" ")

print ("Average CPU utilisation:", responses['Datapoints'][0]['Average'], responses['Datapoints'][0]['Unit'])   #displaying values to terminal
print ("--------------------------------------------------------------------------")
print ("Average CPU Network Out:", res['Datapoints'][0]['Average'], res['Datapoints'][0]['Unit'])
print ("--------------------------------------------------------------------------")
print ("--------------------------------------------------------------------------")
print ("**************************The End*****************************************")
