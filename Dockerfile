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

RUN apt install wget


RUN wget https://exiftool.org/Image-ExifTool-10.98.tar.gz
	https://exiftool.org/Image-ExifTool-12.40.tar.gz
RUN tar -xvzf Image-ExifTool-10.98.tar.gz 
RUN cd Image-ExifTool-10.98/
RUN perl Makefile.PL 
RUN make test
RUN make install


ADD environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml

# Pull the environment name out of the environment.yml
RUN echo "source activate $(head -1 /tmp/environment.yml | cut -d' ' -f2)" > ~/.bashrc
ENV PATH /opt/conda/envs/$(head -1 /tmp/environment.yml | cut -d' ' -f2)/bin:$PATH