#!/usr/bin/env -S jq -rf
def interesting: [ .[].products[] | select(.seen and (.completed | not) and .interesting) ];
def unseen: [ .[].products[] | select((.seen | not) and (.completed | not)) ];

def earliest_end_time:
  map(
      .purchase_type
    | try strptime("%Y-%m-%dT%H:%M:%S") catch empty
    | mktime
    | . - now
    | select(. > 0)
  )
  | min
  | nulls
  | try [. / 86400 | floor, . % 86400 / 3600 | floor, . % 3600 / 60 | floor] catch empty
  ;

def null_time: any(.purchase_type == null);

def buy_any_now: any((.purchase_type == "buy_it_now") or (.purchase_type == "best_offer"));

def summarize(name; f):
  {
    (name + "_time"): (f | earliest_end_time // null),
    (name + "_buy_now"): (f | buy_any_now | if . then "!" else "" end),
    (name + "_null"): (f | null_time | if . then "?" else "" end),
  }
  ;

interesting | earliest_end_time
#summarize("interesting"; interesting) + summarize("unseen"; unseen)
# | [ "<span color='#"
#   , if .unseen_buy_now == "!" or .unseen_time[0] == 0 then "ff0000" else "ffffff" end
#   , "'>"
#   , (.interesting_time | values | "\(.[0])d \(.[1])h \(.[2])m" // "")
#   , .interesting_buy_now
#   , .interesting_null
#   , ","
#   , (.unseen_time | values | "\(.[0])d \(.[1])h \(.[2])m" // "")
#   , .unseen_buy_now
#   , .unseen_null
#   , "</span>"
#   ]
# | add
