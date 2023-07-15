#!/usr/bin/env bash
function yes_or_no {
    while true; do
        read -p "$* [y/n]: " yn
        case $yn in
            [Yy]*) return 0 ;;
            [Nn]*) return 1 ;;
        esac
    done
}

products=$(mktemp)
echo $products >&2
jq -r 'to_entries[] | .key as $key | .value.products[] | select((.seen | not) and (.completed | not)) | "\($key) \(.id) \(.url)"' ~/ebay.json >$products
cat $products

while read -u 3 key id url; do
  echo KEY $key
  echo ID $id
  echo URL $url
  surf "$url" 2>/dev/null &
  interesting=$(yes_or_no && echo true || echo false)
  echo $interesting
  jq ".[\"$key\"].products[\"$id\"].interesting = $interesting" ~/ebay.json | sponge ~/ebay.json
  jq ".[\"$key\"].products[\"$id\"].seen = true" ~/ebay.json | sponge ~/ebay.json
  pkill -P $$
done 3<$products

rm $products
