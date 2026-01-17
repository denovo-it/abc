#!/bin/bash
# Copyright Axelera AI, 2025

_self="${0##*/}"

VAR_docker_users=

ARGL_keep=true
ARGL_containers_only=false
ARGL_ncpu=$(nproc)
ARGL_ngpu="all"
ARGL_list=false
ARGL_delete=false
ARGL_dry_run=false
ARGL_verbose=false
ARG_tag=

VAR_HELP_EXIT_CODE=0

# a few printy things copied from install.sh
# because we can't source it before processing command line etc
bold() {
  if [ -t 1 ]; then
    printf "\e[1m%s\e[m" "$1"
  else
    echo -n "$1"
  fi
}

error_print() {
  bold "ERROR"
  echo ": $*"
} >&2

error() {
  error_print "$@"
  exit 1
}

# Transform long options to short ones
_ignore=
for arg in "$@"; do
  shift
  case "$_ignore$arg" in
    "--keep")        set -- "$@" "-k" ;;
    "--no-keep")     set -- "$@" "-K" ;;
    "--tag")         set -- "$@" "-t" ;;
    "--containers")  set -- "$@" "-c" ;;
    "--cpu")         set -- "$@" "-C" ;;
    "--list")        set -- "$@" "-l" ;;
    "--delete")      set -- "$@" "-d" ;;
    "--verbose")     set -- "$@" "-v" ;;
    "--dry-run")     set -- "$@" "-n" ;;
    "--help")        set -- "$@" "-h" ;;
    --?*)            error_print Invalid option: $arg
                     error_print
                     set -- "-h"
                     VAR_HELP_EXIT_CODE=1
                     break
                     ;;
    "--")            _ignore="ignore"
                     set -- "$@" "$arg"
                     ;;
    *)               set -- "$@" "$arg"
  esac
done

# Parse command-line options
while getopts ":C:t:lvhdnkKc-" opt; do
  case $opt in
    - )
      break
      ;;
    k )
      ARGL_keep=true
      ;;
    K )
      ARGL_keep=false
      ;;
    c )
      ARGL_containers_only=true
      ;;
    C )
      ARGL_ncpu="$OPTARG"
      ;;
    d )
      ARGL_delete=true
      ;;
    t )
      ARG_tag="$OPTARG"
      ;;
    l )
      ARGL_list=true
      ;;
    n )
      ARGL_dry_run=true
      ;;
    v )
      ARGL_verbose=true
      ;;
    h )
      echo "Usage:"
      echo "  $_self [options]"
      echo
      echo "Launch Axelera Docker"
      echo
      echo "  -k --keep         keep the created container (default: keep) (-K --no-keep supported)"
      echo "  -t --tag TAG      specify Docker tag (default based on YAML)"
      echo "  -l --list         list Axelera Docker images and associated containers and volumes"
      echo "                    (can be combined with --tag and/or --containers)"
      echo "  -d --delete       delete Axelera Docker images and associated containers and volumes"
      echo "                    (can be combined with --tag and/or --containers, otherwise deletes all)"
      echo "  -c --containers   for use with --list and --delete to only list/delete containers"
      echo "  -C --cpu [n]      specify number of CPUs (default: $ARGL_ncpu)"
      echo "  -v --verbose      enable verbose output"
      echo "  -n --dry-run      show, but do not execute the docker run command"
      echo "  -h --help         display this help and exit"
      echo
      echo "Any arguments following '--' are passed verbatim to 'docker run'"
      exit $VAR_HELP_EXIT_CODE
      ;;
    \? )
      error_print "Invalid option: -$OPTARG" >&2
      error "Try '$_self --help' for a list of supported options"
      ;;
    : )
      if [ "$OPTARG" == "C" ]; then
        error "Missing option argument for --cpu" >&2;
      elif [ "$OPTARG" == "t" ]; then
        error "Missing option argument for --tag" >&2;
      else
        error "Missing option argument for -$OPTARG" >&2;
      fi
      ;;
    * )
      error_print "Invalid option: -$OPTARG" >&2
      error "Try '$_self --help' for a list of supported options"
  esac
done

# shellcheck disable=SC2004
shift $((OPTIND-1))

ARGL_extra_args="$*"
if [[ -n "$ARGL_extra_args" ]]; then
  if [[ -n "$_ignore" ]]; then
    $ARGL_verbose && echo -e "Passing extra arguments to 'docker run':\n\t$ARGL_extra_args"
  else
    error_print "Extra argument(s) detected: ${1}"
    error_print "Try '$_self --help' for a list of supported options"
    error "or use -- <args> to pass them to 'docker run'"
  fi
fi

# Source install script to check docker installation is OK and
# obtain configuration settings

VAR_launch_docker=true
VAR_installed_cuda_runtime=
VAR_target_container=
VAR_target_container_tag=
AX_docker_system_component=
STATUS_container=
source "install.sh"

if $ARGL_list; then
  if [[ ! -n "$(which docker)" ]]; then
    error "Docker not installed"
  fi
  if ! $ARGL_containers_only; then
    sg "docker" "docker image ls" | grep -E "^(REPOSITORY|axelera/.*${ARG_tag})"
    echo
    sg "docker" "docker volume ls" | grep -E "(VOLUME NAME|axelera_${ARG_tag})"
    echo
  fi
  exec sg "docker" "docker container ls --all" | grep -E "(CONTAINER ID|axelera_${ARG_tag})"
  exit 1
fi

if $ARGL_delete; then
  if [[ ! -n "$(which docker)" ]]; then
    error "Docker not installed"
  fi
  containers=$(sg "docker" "docker container ls --all" | grep -E "axelera_${ARG_tag}" | awk '{print $1}')
  containers=${containers//$'\n'/ }
  if $ARGL_containers_only; then
    if [[ -z "$containers" ]]; then
      echo "No Axelera Docker containers found"
      exit 0
    fi
    echo "Removing Axelera Docker containers:"
  else
    images=${VAR_target_container}${ARG_tag:+:$ARG_tag}
    images=$(sg "docker" "docker images -q ${images}")
    volumes=$(sg "docker" "docker volume ls" | grep -E "axelera_${ARG_tag}" | awk '{print $2}')
    images=${images//$'\n'/ }
    volumes=${volumes//$'\n'/ }
    if [[ -z "$images$volumes$containers" ]]; then
      echo "No Axelera Docker images, containers or volumes found"
      exit 0
    fi
    echo "Removing Axelera Docker images, containers and/or associated volumes:"
  fi
  if [[ -n "$images" ]]; then
    echo
    sg "docker" "docker image ls" | grep -E "(^REPOSITORY|${images// /|})"
  fi
  if [[ -n "$volumes" ]]; then
    echo
    sg "docker" "docker volume ls" | grep -E "(VOLUME NAME|${volumes// /|})"
  fi
  if [[ -n "$containers" ]]; then
    echo
    sg "docker" "docker container ls --all" | grep -E "(CONTAINER ID|${containers// /|})"
  fi
  if response_is_yes "Confirm delete?"; then
    if [[ -n "$containers" ]]; then
      sg "docker" "docker container rm -f ${containers}"
    fi
    if [[ -n "$images" ]]; then
      sg "docker" "docker image rm ${images}"
    fi
    if [[ -n "$volumes" ]]; then
      sg "docker" "docker volume rm ${volumes}"
    fi
  fi
  exit 0
fi

# Check Docker is installed
if needed "$AX_docker_system_component"; then
  error_print "Docker installation required"
  error "First run './install.sh --docker'"
fi

# Check Docker container is available
if ! streq "$STATUS_container" "$STR_ok"; then
  error_print "Docker image $VAR_target_container with tag $VAR_target_container_tag not found on system"
  error "First run './install.sh --docker'"
fi

# Check if container already exists
container_name="axelera_$VAR_target_container_tag"
container_exists=$(sg "docker" "docker ps -a --format '{{.Names}}' | grep -w $container_name" 2>/dev/null || true)

if [ -n "$container_exists" ]; then
  use_autoremove=false
  if [[ $(sg "docker" "docker inspect -f '{{.HostConfig.AutoRemove}}' $container_name" 2>/dev/null || true) == "true" ]]; then
    autoremove=true
  else
    autoremove=false
  fi
  if $autoremove; then
    bold "Warning"
    echo ": There is an existing container set to auto-remove."
    echo "This cannot be unset and the container will be removed when it exits."
    if response_is_yes "Do you want to attach to this container?"; then
      use_autoremove=true
    fi
  fi
  if ($ARGL_keep && ! $autoremove) || $use_autoremove; then
    # Container exists and --keep is set, check if it's running
    container_running=$(sg "docker" "docker ps --format '{{.Names}}' | grep -w $container_name" 2>/dev/null || true)
    if [ -n "$container_running" ]; then
      echo "Attaching to existing running container: $container_name"
      attach="docker attach $container_name"
    else
      echo "Starting and attaching to existing container: $container_name"
      attach="docker start -ai $container_name"
    fi
    ($ARGL_verbose || $ARGL_dry_run) && echo "${attach}"
    $ARGL_dry_run && exit 0
    exec sg "docker" "${attach}"
  else
    # Container exists but --keep is not set, prompt user to remove it
    $autoremove || echo "Container $container_name already exists."
    if response_is_yes "Remove existing container and create a new one?"; then
      remove="docker rm -f $container_name"
      ($ARGL_verbose || $ARGL_dry_run) && echo "${remove}"
      $ARGL_dry_run && exit 0
      sg "docker" "${remove}" || \
        error "Failed to remove existing container. Please remove it manually with: docker rm -f $container_name"
      echo "Container removed. Proceeding with launch..."
    elif $autoremove; then
      error "Cannot proceed. Either agree to attach to the existing container or remove it first"
    else
      error "Cannot proceed. Either use --keep to attach to the existing container or remove it first"
    fi
  fi
fi

# Create launch command
launch="docker run"
if ! $ARGL_keep; then
  launch="$launch --rm"
fi
launch="$launch --name $container_name --cpus $ARGL_ncpu"
launch="$launch --hostname=docker --add-host=docker:127.0.0.1 --privileged --network=host"

# Map UID/GID and home directory
launch="$launch --user $USER"
launch="$launch -v /etc/passwd:/etc/passwd:ro -v /etc/group:/etc/group:ro"
launch="$launch -v /dev:/dev"
launch="$launch -v $HOME:$HOME"

# set up CWD, mapping it to the container if not under $HOME
if [[ "$PWD/" != "$HOME/"* ]]; then
  launch="$launch -v $PWD:$PWD"
fi
launch="$launch -w $PWD"

# map a volume to replace the host .local directory
vol_local="axelera_${VAR_target_container_tag}"
launch="$launch -v ${vol_local}:$HOME/.local"

# X11 display
launch="$launch --ipc host"
launch="$launch --env NO_AT_BRIDGE=1"
launch="$launch --env DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix"

# make X11 work for ssh host
if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ]; then
  XAUTH=/tmp/.docker.xauth_axelera_$VAR_target_container_tag
  if ! $ARGL_dry_run; then
    touch $XAUTH # silence xauth warning
    xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH nmerge -
    chmod 777 $XAUTH
  fi
  launch="$launch -v $XAUTH:$XAUTH -e XAUTHORITY=$XAUTH"
fi

launch="$launch -it -a STDOUT -a STDERR $ARGL_extra_args $VAR_target_container:$VAR_target_container_tag"
launch="$launch bash -c 'make operators-docker; exec bash'"

echo "Launching Docker container"
($ARGL_verbose || $ARGL_dry_run) && echo "$launch"
$ARGL_dry_run && exit 0
exec sg "docker" "$launch"
