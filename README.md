# fargo3d-demo


by Joe Hahn,<br />
joe.hahn@oracle.com,<br />
6 April 2022<br />
git branch=master

this demo creates an HPC cluster within the Oracle cloud OCI, and executes the fargo3d CFD code in parallel on that cluster, stages the fargo3d output in
Object Store, then reads that output into a Data Science notebook where it is visualized. This demo is also summarized in blog post
https://placeholder.url


### create Object Store bucket

1 navigate to OCI console > Storage > Buckets > Create Buckets with

    bucket name=Fargo3DStagingBucket

this staging bucket will be used to communicate HPC output to the Data Science instance

### create HPC cluster

1 log into OCI at https://cloud.oracle.com, click cloud shell icon in upper right corner, then display your public ssh key via

    cat ~/.ssh/id_rsa.pub

2 if your cloud shell account does not yet have an ssh key pair, then create a key pair via

    ssh-keygen -t rsa -P ""

where the -P option means no passphrase

3 navigate to OCI > Marketplace > All Applications > HPC Cluster > Launch Stack with these settings:

    name=fargo3_stack
    tag=None:tag:<your name>
    ssh key: copy/paste above public key
    use custom cluster name=fargo3_stack
    AD=US-ASHBURN-AD-2
    bastion shape=VM.Standard2.4
    boot size=500
    compute shape=BM.HPC2.36
    cluster size=2
    uncheck hyperthreading

4 navigate to OCI > Compute > Instances then use the compartment navigator (lower left box) to find the compartment
where you launched the above stack. Find the *-demo-stack-bastion instance, and note its public IP as bash variable
in your cloud shell session

    IP=132.145.135.54

keeping in mind that the above IP is just an example

5 ssh into cluster's bastion host as user opc 

    ssh opc@$IP

6  note your user and tenancy ocids by navigating to 
OCI console > Profile (upper right corner ) > user (to grab user ocid) & tenancy (to grab tenancy ocid)

    user=ocid1.user.oc1..aaaaaaaafolzomxi6tqsoy6wdnlwj2hxv4ooljhtvfgy4sm722iwxaakgqqq
    tenancy=ocid1.tenancy.oc1..aaaaaaaaiyavtwbz4kyu7g7b6wglllccbflmjx2lzk5nwpbme44mv54xu7dq

keeping in mind that the above ocids are examples

7 configure your ~/.oci/config file on bastion instance so that it can interact with Object Store

    oci setup config

answering all question with default values except for user & tenancy ocids and region index (I entered 35 to select us-ashburn-1)

8 display public key

    cat ~/.oci/oci_api_key_public.pem

9 navigate to OCI console > profile > user settings > API Keys > Add Key > paste above public key

10 test credentials:

    oci os ns get

which should report the name of your tenancy, and tells us that the bastion instance can interact with Object Store buckets.

11 clone repo

    git clone git@129.213.160.170:jhahn/fargo3d-demo.git
    #git clone git@github.com:oracle-nace-dsai/fargo3d-demo.git
    cd fargo3d-demo

12 download and unpack fargo

    wget http://fargo.in2p3.fr/downloads/fargo3d-1.3.tar.gz
    tar -xvf fargo3d-1.3.tar.gz
    cd fargo3d-1.3

13 confirm that openmpi module exists

    module load mpi/openmpi/openmpi-4.0.3rc4
    mpicc --version

14 build fargo3d 

    make SETUP=fargo PARALLEL=1 GPU=0

15 copy fargo_big.par into fargo3d-1.3/setups/fargo:

    cp ../fargo_big.par setups/fargo/fargo.par

this copies parameters for so-called big simulation that resolves the disk 16x more finely
and extends the sim 5x longer in time into setups/fargo folder

16 copy the slurm batch script to the working directory, and inspect

    cp ../MY_SLURM_JOB .
    cat MY_SLURM_JOB

which will load openmpi and then execute fargo3d in parallel

17 submit slurm job

    sbatch --job-name=fargo3d --nodes=2 --ntasks-per-node=32 --cpus-per-task=1 --exclusive MY_SLURM_JOB

job-name=fargo3d that is to be executed on 2 compute nodes using 32 cpus on each node

18 check slurm job queue

    squeue

19 to cancel slurm job

    scancel <JOBID>

20 monitor fargo3d's screen output

    tail -f slurm-<slurm-JOBID>.out

21 use OCI > Compute > instances console to get the private IP of one of the compute nodes:

    IP=172.16.5.172

noting the above IP is merely a placeholder

22 ssh into compute node:

    ssh opc@$IP

23 enter 'top' then '1' to confirm that 28 of the nodes 36 cpus are busy (unsure if this is right...double check)

24 use OCI console to click on one of two <*>-fargo3d-demo-stack compute nodes and check its cpu utilization 

25 slurm job executes in 30.5 minutes

    cd outputs/fargo
    ls

to see output files

26 when fargo3d is executed across 2+ nodes, it doesnt properly merge each node's output (some data gets dropped), so 
so use python script to manually concatenate that output into folder 'concatentated_output'

    cp ../../../concatentate_output.py .
    python3 concatentate_output.py
    ls concatentated_output

27 tar the concatenated output files

    tar -cvzf concatentated_output.tgz concatentated_output

28 copy concatentated_output.tgz to object store usig oci-cli

    bucket_name=Fargo3DStagingBucket
    local_file=concatentated_output.tgz
    os_file=$local_file
    oci os object put --bucket-name $bucket_name --file $local_file --name $os_file --force

29 lastly rerunning the slurm job using single cpu on single node via

    sbatch --job-name=fargo3d --nodes=1 --ntasks-per-node=1 --cpus-per-task=1 --exclusive MY_SLURM_JOB

executes in 1116min=18.6 hours, which is 37 times slower, ie not the expected 2x28=56 slower...


### use Data Science to visualize HPC output

1 launch Data Science (DS) instance in same compartment where you launched you the HPC stack, this demo uses these settings:

    shape=VM.Standard.E3.Flex with 2ocpus, 64Gb
    block storage=1024Gb
    select custom networking
    VCN=fargo3_stack_VCN
    subnet=fargo3_stack_private_subnet

2  repeat above steps 6-11 to connect DS instance to Object Store 

3 install/activate conda

    odsc conda install -s dataexpl_p37_cpu_v3
    conda activate /home/datascience/conda/dataexpl_p37_cpu_v3

4 copy concatentated_output.tgz from OS to DS and then expand:

    bucket_name=Fargo3DStagingBucket
    os_file=concatentated_output.tgz
    oci os object get -bn $bucket_name --name $os_file --file $os_file
    tar -xvf concatentated_output.tgz
    cd concatentated_output

5 cp display_fargo3d_output notebook to working directory

    cp ../display_fargo3d_output.ipynb .

6 use file explorer at left edge to navigate to fargo3d-demo > concatentated_output > display_fargo3d_output.ipynb
and execute that notebook using the dataexpl_p37_cpu_v3 conda, to visualize the HPC output


### delete HPC cluster

1 delete DS instance first, since it depends on HPC cluster's VCN. Or remove it from that VCN

2 when done, navigate to HPC stack:

    OCI > developer services > stacks > fargo3_stack > destroy

3 then more actions > delete stack

