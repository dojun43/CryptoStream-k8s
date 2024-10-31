# 고정 ip
resource "google_compute_address" "master-static-ip" {
  name   = "master-static-ip"
  project = var.project
  region  = var.region
}

resource "google_compute_address" "worker1-static-ip" {
  name   = "worker1-static-ip"
  project = var.project
  region  = var.region
}

resource "google_compute_address" "worker2-static-ip" {
  name   = "worker2-static-ip"
  project = var.project
  region  = var.region
}

# port 허용 
resource "google_compute_firewall" "master-port" {
  name    = "master-port"
  project = var.project
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["6443", "2379-2380", "10250-10252", "10257", "10259"]
  }

    allow {
    protocol = "udp"
    ports    = ["8285", "8472"]
  }

  source_ranges = ["0.0.0.0/0"] 
  target_tags   = ["master-port"]
}

resource "google_compute_firewall" "worker-port" {
  name    = "worker-port"
  project = var.project
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["10250", "30000-32767"]
  }

  allow {
    protocol = "udp"
    ports    = ["8285", "8472"]
  }

  source_ranges = ["0.0.0.0/0"] 
  target_tags   = ["worker-port"]
}

resource "google_compute_firewall" "allow-ssh" {
  name    = "allow-ssh"
  project = var.project
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"] 
  target_tags   = ["allow-ssh"]
}

# gce
resource "google_compute_instance" "k8s-master" {
  name         = "k8s-master"
  machine_type = "e2-medium"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.master-static-ip.address
    }
  }

  metadata_startup_script = file("startup_script.sh")

  tags = ["allow-ssh", "master-port"]
}

resource "google_compute_instance" "k8s-worker1" {
  name         = "k8s-worker1"
  machine_type = "e2-medium"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.worker1-static-ip.address
    }
  }

  metadata_startup_script = file("startup_script.sh")

  tags = ["allow-ssh", "worker-port"]
}

resource "google_compute_instance" "k8s-worker2" {
  name         = "k8s-worker2"
  machine_type = "e2-medium"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.worker2-static-ip.address
    }
  }

  metadata_startup_script = file("startup_script.sh")

  tags = ["allow-ssh", "worker-port"]
}