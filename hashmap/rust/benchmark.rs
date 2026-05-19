use std::collections::HashMap;
use std::env;
use std::process;

const KEY_PREFIX_MISS: u8 = b'B';

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <insert|update|retrieve|miss> <count>", args[0]);
        process::exit(1);
    }

    let mode = &args[1];
    let count: usize = args[2].parse().expect("invalid count");

    let mut h: HashMap<String, usize> = HashMap::new();
    //h.reserve(count);

    for i in 1..=count {
        let key = format!("{}", i);
        h.insert(key, i as usize);
    }

    match mode.as_str() {
        "insert" => {
            process::exit(0);
        }
        "update" => {
            for i in 1..=count {
                let key = format!("{}", i);
                h.insert(key, (i + 1) as usize);
            }
        }
        "retrieve" => {
            for i in 1..=count {
                let key = format!("{}", i);
                if h.get(&key) != Some(&(i as usize)) {
                    process::exit(1);
                }
            }
        }
        "miss" => {
            for i in 1..=count {
                let key = format!("{}{}", KEY_PREFIX_MISS as char, i);
                if h.contains_key(&key) {
                    process::exit(1);
                }
            }
        }
        _ => {
            eprintln!("Invalid mode: {}", mode);
            process::exit(1);
        }
    }
}
