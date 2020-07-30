# django-docker-template

Boilerplate template to start development with Django v3.0.8 and djangorestframework v3.11.0 with postgresSQL database backend inside Docker container.

## Installation

1. Clone Repository
2. install docker-ce or docker desktop
3. add .env file inside src container
4. Build docker containers from the src directory on terminal run docker-compose command

```bash
$> cd src
$> docker-compose up --build
```

5. Now if you go to the [http://localhost:8000/](http://localhost:8000/) you will see django default

## Usage

To run the django application should now be up.
If you are using vscode install the docker plugin and the Remote Development plugin to continue to develop on vscode.
you will require to run the makemigration and migrate commands on django to setup the database for the first time.


## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

Also update the changelog as well [changelog](/changelog.md)

## License

[APACHE 2.0](https://www.apache.org/licenses/LICENSE-2.0)