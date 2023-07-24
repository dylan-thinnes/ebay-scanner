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
  ) | min | try strftime("%-dd %-Hh %Mm") catch "_"
  ;

def null_time: any(.purchase_type == null);

def buy_any_now: any((.purchase_type == "buy_it_now") or (.purchase_type == "best_offer"));

{
  "interesting_time": (interesting | earliest_end_time),
  "interesting_buy_now": (interesting | buy_any_now | if . then "!" else "" end),
  "interesting_null": (interesting | null_time | if . then "?" else "" end),

  "unseen_time": (unseen | earliest_end_time),
  "unseen_buy_now": (unseen | buy_any_now | if . then "!" else "" end),
  "unseen_null": (unseen | null_time | if . then "?" else "" end),
} |

"\(.interesting_time)\(.interesting_buy_now)\(.interesting_null) \(.unseen_time)\(.unseen_buy_now)\(.unseen_null)"
