Software pipeline

* Voyager SDK in Orange Pi 5 Plus

  https://support.axelera.ai/hc/en-us/articles/27059519168146-Bring-up-Voyager-SDK-in-Orange-Pi-5-Plus

NOTE: run the dpkg install indicated and check the cfg/config-ubuntu-2204-arm64.yaml if is in line with the guide before proceeding
  
* Axelera Voyager SDK (starting point)

  https://github.com/denovo-it/voyager-sdk

* Get the token

  https://github.com/axelera-ai-hub/voyager-sdk/blob/release/v1.2.5/docs/tutorials/install.md#generate-a-token-for-the-installer

In voyager-sdk you can find the install_voyager.sh that requires .env populated ( see env_example.txt ) e install the sdk as indicated in the guide.

After the install and a reboot, if everything is ok, you can launch denovo_test.sh in X environment and check if everything runs smoothly.
