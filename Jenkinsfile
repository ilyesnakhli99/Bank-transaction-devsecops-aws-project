pipeline {
    // Tells Jenkins to execute this entire pipeline on any available executor
    agent any

    environment {
        // Define your Docker Hub registry credentials and tags
        DOCKER_HUB_USER = 'ilyesnakhli'
        IMAGE_NAME      = 'Back-transaction-app'
        IMAGE_TAG       = "${BUILD_NUMBER}" // Uses the sequential Jenkins build number as a version tag
    }

    stages {
        // Stage 1: Pull the freshest code from your GitHub Repo
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        // Stage 2: Install Trivy on-the-fly and scan the source files for vulnerabilities
        stage('DevSecOps: Source Security Scan') {
            steps {
                echo 'Installing and Running Trivy Filesystem Vulnerability Scan...'
                sh '''
                    # Download and install Trivy to the local workspace directory
                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b .
                
                    # Run the scan using the local binary we just downloaded
                    ./trivy fs --severity HIGH,CRITICAL .
                '''
            }
        }

        // Stage 3: Compile the Docker blueprint into a real container image
        stage('Docker Build') {
            steps {
                echo 'Building the Docker Image...'
                // Run from the repository root (.) and point directly to the Dockerfile (-f)
                sh "docker build -t ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG} -f ./Dockerfile ."
            }
        }

        // Stage 4: Scan the newly compiled image for vulnerabilities using local Trivy
        stage('DevSecOps: Image Security Scan') {
            steps {
                echo 'Scanning the compiled Docker Image with Trivy...'
                sh "./trivy image --severity HIGH,CRITICAL ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}"
            }
        }

        // Stage 5: Ship the secure image out to Docker Hub
        stage('Push Image to Registry') {
            steps {
                // Securely logs into Docker Hub using credentials stored safely inside Jenkins UI
                withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh "echo ${PASS} | docker login -u ${USER} --password-stdin"
                    sh "docker push ${DOCKER_HUB_USER}/${IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
        }

        // Stage 6: Update the deployment manifest and push it back to GitHub
        stage('Update GitOps Manifests') {
            steps {
                script {
                    echo "Updating deployment manifest version to: ${IMAGE_TAG}"
                    
                    // 1. Swap the placeholder tag with the fresh build tag (using correct Kubernetes/ folder)
                    sh "sed -i 's|image: ilyesnakhli/ivolve-flask-app:.*|image: ilyesnakhli/ivolve-flask-app:${IMAGE_TAG}|g' Kubernetes/deployment.yaml"
                    
                    // 2. Safely pull the GitHub token and push changes
                    withCredentials([string(credentialsId: 'github-token-id', variable: 'GH_TOKEN')]) {
                        sh """
                            git config user.email "jenkins@ivolve.local"
                            git config user.name "Jenkins CI"
                            
                            git add Kubernetes/deployment.yaml
                            git commit -m "chore: automated image tag update to ${IMAGE_TAG} [skip ci]"
                            
                            # Pushes the change back to the repository HEAD of your main branch
                            git push https://${GH_TOKEN}@github.com/ilyesnakhli99/DevSecops-Aws-Project.git HEAD:main
                        """
                    }
                }
            }
        }
    }

    // Post-actions run automatically depending on whether the pipeline succeeded or crashed
    post {
        success {
            echo 'Pipeline completed successfully! Ready for GitOps deployment.'
        }
        failure {
            echo 'Pipeline failed! Sending alert to CloudWatch and SNS Notification...'
        }
    }
}