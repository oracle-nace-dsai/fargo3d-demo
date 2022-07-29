#concatentate_output.py
#
#by Joe Hahn
#joe.hahn@oracle.com
#11 May 2022
#
#concatenate fargo3d's output

#to execute:
#    python3 #concatentate_output.py

#get list of all files
import os
all_files = os.listdir()
print (all_files[0:3])

#list of various filetypes
file_types = ['gasdens', 'gasenergy', 'gasvx', 'gasvy']

#create destination folder
destination_folder = 'concatentated_output'
os.mkdir(destination_folder)

#loop over all file_types
for file_type in file_types:
    
    #get list of all relevant files
    files = [file for file in all_files if (file_type in file)]
    print ('files[0:3] = ', files[0:3])

    #generate lists of all times and segments written by various nodes
    times = []
    segments = []
    for file in files:
        spl = file.split('_')
        time = spl[0].replace(file_type, '')
        segment = spl[1].split('.')[0]
        if (time not in times):
            times += [int(time)]
        if (segment not in segments):
            segments += [int(segment)]
    times = list(set(times))
    segments = list(set(segments))
    times.sort()
    segments.sort()
    print ('times = ', times)
    print ('segments = ', segments)
    
    #for each time generate & execute bash command that concatenats all segments
    for time in times:
        cmd = 'cat '
        for segment in segments:
            file = file_type + str(time) + '_' + str(segment) + '.dat'
            cmd += file + ' '
        cmd += '> ' + destination_folder + '/' + file_type + str(time) + '.dat'
        print ('cmd = ', cmd)
        r = os.system(cmd)

#cp variables.par and domain_*.dat into fargo folder
cmd = 'cp variables.par domain_*.dat ' + destination_folder + '/.'
r = os.system(cmd)
