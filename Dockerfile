# FROM defines the base image
FROM conda/miniconda3
MAINTAINER Patrick Gray <pgrayobx@gmail.com>

# don't want to be updating but need to in order to use opencv
RUN apt update
RUN apt -y install libgl1-mesa-glx
RUN apt-get update
RUN apt-get install zbar-tools -y

# maybe don't need this
RUN apt install libzbar0
RUN apt install make

ADD environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml

# set it to by default activate this conda env
RUN echo "source activate dronewq" > ~/.bashrc
ENV PATH /opt/conda/envs/dronewq/bin:$PATH

# this tool was built in the exact same env and we're copying it in here to the correct dir
# this isn't working though
#COPY exiftool /usr/local/envs/dronewq/bin/exiftool