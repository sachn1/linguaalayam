terraform {
  backend "gcs" {
    bucket = "linguaalayam-tfstate"
    prefix = "linguaalayam"
  }
}
