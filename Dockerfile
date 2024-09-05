# FROM defines the base image
FROM continuumio/miniconda3
MAINTAINER Patrick Gray <pgrayobx@gmail.com>

RUN apt update
RUN apt -y install libgl1-mesa-glx
RUN apt-get update
RUN apt-get install zbar-tools -y

RUN apt install libzbar0
RUN apt install make

RUN conda update conda

ADD environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml

### set it to by default activate this conda env
RUN echo "source activate dronewq" > ~/.bashrc
ENV PATH /opt/conda/envs/dronewq/bin:$PATH

### after running go into the Docker container and run these commands to install exiftool
### the version we have on Dockerhub clifgray/dronewq:v3 already has this installed
# cd /srv/
# wget https://cpan.metacpan.org/authors/id/E/EX/EXIFTOOL/Image-ExifTool-12.15.tar.gz
# tar -xvzf Image-ExifTool-12.15.tar.gz 
# cd Image-ExifTool-12.15/
# perl Makefile.PL 
# make test
# make install
# then you will need to commit this container back to the image 