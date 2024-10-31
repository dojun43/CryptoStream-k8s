## install k8s
echo "Starting k8s installation" >> /var/log/startup_script.log

# swap off
sudo swapoff -a
sudo sed -i '/swap/s/^/#/' /etc/fstab

# IPv4 packet forwarding
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.ipv4.ip_forward = 1
EOF

sudo sysctl --system

# install package
sudo apt-get update

# install Container Runtime 
sudo apt install -y containerd=1.7.12-0ubuntu2~22.04.1

sudo mkdir -p /etc/containerd && containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
       
sudo systemctl restart containerd
sudo systemctl enable containerd

# install k8s package
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.31/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update

VERSION=1.31.1-1.1
sudo apt-get install -y kubelet=$VERSION kubeadm=$VERSION kubectl=$VERSION
sudo apt-mark hold kubelet kubeadm kubectl

sudo systemctl start kubelet
sudo systemctl enable kubelet

echo "End k8s installation" >> /var/log/startup_script.log

# git clone
sudo -H bash -c "mkdir -p /mnt/dataloader-pv && cd /mnt/dataloader-pv && git clone https://github.com/dojun43/CryptoStream-k8s.git"
sudo -H bash -c "mkdir -p /mnt/dataloader-pv && cd /mnt/dataloader-pv && git clone https://github.com/dojun43/CryptoStream-k8s.git"