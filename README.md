Please see web site for information: http://bots.sourceforge.net
Most documentation is on the wiki: http://code.google.com/p/bots/wiki/StartIntroduction
Bots is licenced under GNU GENERAL PUBLIC LICENSE Version 3; for full text: http://www.gnu.org/copyleft/gpl.html
Commercial support by EbberConsult, http://www.ebbersconsult.com

---

### Deployment Structure

```
/ 
├── src/
│   └── bots/
│       ├── botssys/
│       ├── usersys/
│       ├── config/
│       ├── templates/
│       ├── views.py
│       ├── urls.py
│       └── ...
├── deploy/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env
├── .env.example
├── README.md
└── requirements.txt
```

---

## Notable Adjustments

- The project has been restructured to use a `src/` folder. All Bots application code now lives under `src/bots/`.
- Docker deployment is organized under the `deploy/` folder, which contains the `Dockerfile` and `docker-compose.yml`.
- Environment variables (like database settings) are now handled through a `.env` file at the project root.
- A `.env.example` is provided to show required variables without exposing sensitive credentials.
- If you are using SQLite instead of Postgres, you do not need to define the database-related environment variables (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).
- For SQLite setups, the application will automatically initialize a local database file during container startup.

---

## Running with Docker

1. Copy the example env:
   ```bash
   cp .env.example .env
   ```
     Fill in your database connection info.
  
2. Build and start everything:
   ```bash
   docker-compose up --build
   ```
3. Access the Bots web interface at:
   ```bash
   http://localhost:8080
   ```

---

## Running with Kubernetes

Bots can also be deployed to a Kubernetes cluster using `kubectl` and `kustomize`.

### 1. Prepare Environment Files

- Update the values in the the **Example secret files** located in the  k8s/overlays/production/ directory:
    
    ```bash
    `cp k8s/overlays/production/bots-secret.example.yaml k8s/overlays/production/bots-secret.yaml`
    `cp k8s/overlays/production/bots-configmap.example.yaml k8s/overlays/production/bots-configmap.yaml`
    ```
    
---

### 2. Deploy to Kubernetes

Run the following command from the project root:

```bash

`kubectl apply -k k8s/overlays/production`
```
This will:

- Deploy the Bots webserver, dirmonitor, and jobqueue as Kubernetes Deployments.
- Expose the services via a Kubernetes `Service`.
- Create environment `ConfigMap` and `Secrets`.