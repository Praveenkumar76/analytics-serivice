pipeline {
    agent any

    triggers {
        pollSCM('* * * * *')
    }

    environment {
        REGISTRY = "praveenkumarr46"
        IMAGE_NAME = "analytics-service"
        GITOPS_REPO = "github.com/Praveenkumar76/URL-shortener-gitops.git"
        GITOPS_BRANCH = "main"
        SERVICE_DIR = "services/analytics-service"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Docker Build') {
            steps {
                script {
                    env.GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
                }
                sh """
                if [ -d "${SERVICE_DIR}" ]; then
                    cd ${SERVICE_DIR}
                fi
                docker build -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} -t ${REGISTRY}/${IMAGE_NAME}:latest .
                """
            }
        }

        stage('Docker Push') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-hub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
                    sh "docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
                    sh "docker push ${REGISTRY}/${IMAGE_NAME}:latest"
                }
            }
        }

        stage('Update GitOps Manifest') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'github-creds',
                    usernameVariable: 'GIT_USER',
                    passwordVariable: 'GIT_PASS'
                )]) {
                    sh """
                    rm -rf gitops-repo
                    git clone -b ${GITOPS_BRANCH} https://${GIT_USER}:${GIT_PASS}@${GITOPS_REPO} gitops-repo
                    cd gitops-repo

                    # Run these INSIDE the cloned folder WITHOUT the --global flag
                    git config user.name "Jenkins CI"
                    git config user.email "jenkins-ci@local"

                    sed -i.bak "s|image: ${REGISTRY}/${IMAGE_NAME}:.*|image: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g" apps/${IMAGE_NAME}/base/deployment.yaml
                    rm -f apps/${IMAGE_NAME}/base/deployment.yaml.bak

                    git add apps/${IMAGE_NAME}/base/deployment.yaml
                    git commit -m "chore(gitops): auto-promote ${IMAGE_NAME}:${IMAGE_TAG} [skip ci]"
                    git push origin ${GITOPS_BRANCH}
                    """
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
