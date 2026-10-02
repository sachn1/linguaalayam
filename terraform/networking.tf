resource "google_compute_network" "linguaalayam" {
  name                    = "linguaalayam-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "linguaalayam" {
  name                     = "linguaalayam-subnet"
  network                  = google_compute_network.linguaalayam.id
  region                   = var.region
  ip_cidr_range            = "10.10.0.0/24"
  private_ip_google_access = true
}

# reserved static external IP
resource "google_compute_address" "nat_ip" {
  name   = "linguaalayam-nat-ip"
  region = var.region
}

# router for NAT
resource "google_compute_router" "linguaalayam" {
  name    = "linguaalayam-router"
  network = google_compute_network.linguaalayam.id
  region  = var.region
}

resource "google_compute_router_nat" "linguaalayam" {
  name                               = "linguaalayam-nat"
  router                             = google_compute_router.linguaalayam.name
  region                             = var.region
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = [google_compute_address.nat_ip.self_link]
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.linguaalayam.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}
