# DroneWQ Backend Documentation
---

## Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Building the Electron app](#building-the-electron-app)
4. [Testing](#testing)

---

## Overview

### Purpose

The DroneWQ backend is a flask server that responds to the frontend's requests.
It serves as the bridge between the `DroneWQ` library and the frontend.

### Design Intention

- **Web App Architecture**: We chose this architecture because it was the Most
    familiar to us. Electron and python also enabled us to target multiple OS supports.
    However, that came with a cost as packaging python inside the app makes it ~4GB
    big.
    > In the future, I recommend making a script that install the python environment on the users machine.
    > If so, remember to require conda from users.
    >
    > This will be no different than a docker image though. Maybe having the
    > backend/server in a docker image is more correct...
- **Shipping Conda env with the app**: Conda is incredible. It can locally download
    external dependencies like `exiftool` and `zbar`.
    Our core sub-package for called `micasense` used external dependencies and we
    needed to find a solution to install them on user's machine. 

    Sometimes, `pyzbar`, `zbar`'s python interface, would not find the system `zbar`
    installation. In that case, I had to manually soft-link it through the terminal.
    I would not wish that for the users, so I just shipped the entrire pre-installed
    env with the app. 

    Now, was that a good idea? I don't know. Probably not. Once again, in the future,
    we have to fix this.
- **Modular as possible**: Tried to make the backend as modular so that you can plug in and out different
    stuff and have the app stil work.
    > There are outliers like the `pipeline.py` and `projects.py`.
    > Should break these down further.
- **SQLite DB**: SQLite is very small and can be shipped with python.
    It is used to manage project instances, such as project name, settings, path, etc.
- **Accessible project folders**: Everything will happen in the project folder
    the user chose. This is to give the users the freedom to manipulate the
    project dataset and intermediate results. Just as the original package intended.
- **Error Handling**: I tried to handle as much errors possible.
    But with my given experience, I don't think it is as comprehensive as it should
    be. 
- **Why Flask**: Flask is lightweight. We also did not concern ourselves with security,
    since the app will be completely local with no connection to the internet or networks.

### Technology Stack

- **Flask**: Lightweight Backend Framework
- **SQLite**: Another lightweight database
- **Python** 

---

### Communication Flow

Since flask is in python, I can directly import the package and work with it.

---

## File Structure

```
app
├── app_ui.js
├── backend             <--- Backend lives here
├── charts.js
├── csv_handler.js
├── dashboard.js
├── dist                <--- This will be created after you build the electron app
├── image_handler.js
├── main.js
├── mosaic_handler.js
├── node_modules
├── package-lock.json
├── package.json
├── project_settings.js
├── projects.db
├── python              <--- Conda environment that is shipped with the app
├── trajectory_handler.js
├── upload.js
└── wireframes
```

---

## Building the electron app

This is the exact method I used to build the Dronewq.dmg build.

### 1. Create a minimal conda env

You have to create the most minimal conda env possible so that the app size
doesn't blow up. I would usually create a conda env dedicated to building the app
and then not install anything except the `environement.yml` and the `dronewq` package.

### 2. Copy that env to the app directory

You can see lists of envs you have with:
```
conda env list
```
It should show you the paths of those envs, like so:
```bash
# conda environments:
#
base                   /opt/anaconda3
dronewq                /opt/anaconda3/envs/dronewq
```

I would then go to the app directory, and copy that env as "python":
```bash
cd app
cp -r /opt/anaconda3/envs/dronewq python
```

### 3. Electron build

We are using [electron-builder](https://www.electron.build/) because I read this [guide](https://til.simonwillison.net/electron/python-inside-electron).  

Anyway, to build the app, you can run:
```bash
npm run app:dir
```

This will start building mac executable binary. We haven't tested other OS at the moment.

> [!NOTE]
> It will ask you to sign the app or start signing. You can <ctrl-c> and it will stop signing and the app will still be there.
> Currently, we don't really sign the app.

---

## Testing

Currently, the backend doesnt' have any testing.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
