#!/bin/bash

BASE_URL="https://oem-share.canonical.com/partners"
DCD_FILE="/run/mnt/ubuntu-seed/.disk/info"

convert_to_url() {
  local input_string="$1"
  # Examples:
  # canonical-oem-carlsbad:element-v2-uc24:20241205.15:v2-uc24-x01
  # canonical-oem-shiner:x8high-som-pdk:20241209-10:
  # canonical-oem-denver::20241201-124:

  if [[ "$input_string" =~ ^canonical-oem-([a-zA-Z0-9]+):([a-zA-Z0-9-]*):([0-9.-]+)(:(.*))?$ ]]; then
    # Rule 1: Input string must start with "canonical-oem-" Mandatory
    # Rule 2: Project Name (alphabets and numbers) - Mandatory
    # Rule 3: Series (alphabets, numbers, and dash "-") - Optional
    # Rule 4: Build ID (Numbers, dot ".", and dash "-") - Mandatory
    # Rule 5: Additional Information (No limitation) - Optional
    local project_name="${BASH_REMATCH[1]}"
    local series="${BASH_REMATCH[2]}"  # optional
    local build_id="${BASH_REMATCH[3]}"
    local additional_info="${BASH_REMATCH[4]}"  # optional
    local image_name=""

    if [ -n "$series" ]; then
      image_name="${project_name}-${series}-${build_id}.img"
      echo "$BASE_URL/${project_name}/share/${series}/${build_id}/${image_name}"
    else
      image_name="${project_name}-${build_id}.img"
      echo "$BASE_URL/${project_name}/share/${build_id}/${image_name}"
    fi
  else
    echo "Invalid input format: $input_string" >&2
    return 1
  fi
}

if [ -f "$DCD_FILE" ]; then
  dcd_string=$(cat "$DCD_FILE")
  url=$(convert_to_url "$dcd_string")
  echo "$url"
  exit 0
else
  echo "DCD file not found: $DCD_FILE" >&2
  #exit 1
fi

echo "---UT---"
echo "# all fields"
input1="canonical-oem-carlsbad:element-v2-uc24:20241205.15:v2-uc24-x01"
echo "DCD string: $input1"
convert_to_url "$input1"

echo
echo "# no additional info"
input2="canonical-oem-shiner:x8high-som-pdk:20241209-10:"
echo "DCD string: $input2"
convert_to_url "$input2"

echo
echo "# no series and addtional info"
input3="canonical-oem-denver::20241201-124:"
echo "DCD string: $input3"
convert_to_url "$input3"

echo
echo "# no additional info"
input4="canonical-oem-foobar:test-series:20250327.01"
echo "DCD string: $input4"
convert_to_url "$input4"

echo
echo "# no series and no additional info"
input5="canonical-oem-another::20250327.02"
echo "DCD string: $input5"
convert_to_url "$input5"

echo
echo "# invalid format - missing canonical-oem-"
input6="oem-only-test:series:build"
echo "DCD string: $input6"
convert_to_url "$input6"

echo
echo "# invalid format - project name with invalid characters"
input7="canonical-oem-Project-Name:series:build"
echo "DCD string: $input7"
convert_to_url "$input7"

echo
echo "# invalid format - build id with invalid characters"
input8="canonical-oem-project:series:build_id:info"
echo "DCD string: $input8"
convert_to_url "$input8"

echo
echo "# valid format - series with dash"
input9="canonical-oem-validproject:ubuntu-22.04:20250327:extra"
echo "DCD string: $input9"
convert_to_url "$input9"

echo
echo "# valid format - project name with numbers"
input10="canonical-oem-project123:series:20250327:extra"
echo "DCD string: $input10"
convert_to_url "$input10"
