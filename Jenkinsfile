pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    some-label: jenkins-agent
spec:
  containers:
  # The standard Jenkins agent container
  - name: jnlp
    image: jenkins/inbound-agent:3383.vc8881d4b_0e76-1
  # A container with the Docker CLI installed
  - name: docker
    image: docker:24.0.7-cli
    command:
    - cat
    tty: true
    volumeMounts:
    - mountPath: /var/run/docker.sock
      name: docker-sock
  volumes:
  - name: docker-sock
    hostPath:
      path: /var/run/docker.sock
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

        stage('Docker Build') {
            steps {
                // Force this stage to run inside the container that actually has the 'docker' command!
                container('docker') {
                    echo 'Building the Docker Image...'
                    sh "docker build -t ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} -f ./Dockerfile ."
                }
            }
        }

        stage('DevSecOps: Image Security Scan') {
            steps {
                echo 'Scanning the compiled Docker Image with Trivy...'
                sh "./trivy image --severity HIGH,CRITICAL ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}"
            }
        }

        stage('Push Image to Registry') {
            steps {
                // Force this stage to run inside the 'docker' container so it can run 'docker login/push'
                container('docker') {
                    withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                        sh "echo ${PASS} | docker login -u ${USER} --password-stdin"
                        sh "docker push ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}"
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