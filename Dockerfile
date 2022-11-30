# FROM defines the base image
FROM continuumio/anaconda3
MAINTAINER Patrick Gray <pgrayobx@gmail.com>

# don't want to be updating but need to in order to use opencv
#RUN apt update
#RUN apt -y install libgl1-mesa-glx
#RUN apt-get update
#RUN apt-get install zbar-tools -y

# maybe don't need this
#RUN apt install libzbar0
#RUN apt install make

ADD environment_tmp.yml /tmp/environment_tmp.yml
RUN conda env create -f /tmp/environment_tmp.yml

# set it to by default activate this conda env
RUN echo "source activate dronewq" > ~/.bashrc
ENV PATH /opt/conda/envs/dronewq/bin:$PATH