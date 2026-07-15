pipeline {
    // We define our Agent as a dynamic Kubernetes Pod containing a Kaniko container
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: jenkins-agent
spec:
  containers:
  # The default Jenkins execution agent
  - name: jnlp
    image: jenkins/inbound-agent:3383.vc8881d4b_0e76-1
  # The Kaniko container used specifically to build and push images
  - name: kaniko
    image: gcr.io/kaniko-project/executor:v1.20.0-debug
    command:
    - sleep
    args:
    - 9999999
'''
        }
    }

    environment {
        DOCKER_HUB_USER = 'ilyesnakhli'
        IMAGE_NAME      = 'Back-transaction-app'
        IMAGE_TAG       = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('DevSecOps: Source Security Scan') {
            steps {
                echo 'Installing and Running Trivy Filesystem Vulnerability Scan...'
                sh '''
                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b .
                    ./trivy fs --severity HIGH,CRITICAL .
                '''
            }
        }

        // Build and push are handled in one secure step by Kaniko!
        stage('Docker Build & Push') {
            steps {
                // Switch execution to the 'kaniko' container defined in our Pod Template
                container('kaniko') {
                    echo 'Building and Pushing the Docker Image with Kaniko...'
                    
                    // Pulling Docker Hub credentials securely from Jenkins
                    withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                        sh """
                            # Generate a Docker config file containing credentials so Kaniko can authenticate
                            mkdir -p /kaniko/.docker
                            echo '{"auths":{"https://index.docker.io/v1/":{"username":"'\$USER'","password":"'\$PASS'"}}}' > /kaniko/.docker/config.json
                            
                            # Execute Kaniko to build the Dockerfile and push directly to Docker Hub
                            /kaniko/executor \
                                --context=${WORKSPACE} \
                                --dockerfile=${WORKSPACE}/Dockerfile \
                                --destination=${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}
                        """
                    }
                }
            }
        }

        stage('Update GitOps Manifests') {
            steps {
                script {
                    echo "Updating deployment manifest version to: ${IMAGE_TAG}"
                    sh "sed -i 's|image: ilyesnakhli/ivolve-flask-app:.*|image: ilyesnakhli/ivolve-flask-app:${IMAGE_TAG}|g' Kubernetes/deployment.yaml"
                    
                    withCredentials([string(credentialsId: 'github-token-id', variable: 'GH_TOKEN')]) {
                        sh """
                            git config user.email "jenkins@ivolve.local"
                            git config user.name "Jenkins CI"
                            git add Kubernetes/deployment.yaml
                            git commit -m "chore: automated image tag update to ${IMAGE_TAG} [skip ci]"
                            git push https://${GH_TOKEN}@github.com/ilyesnakhli99/DevSecops-Aws-Project.git HEAD:main
                        """
                    }
                }
            }
        }
    }
}