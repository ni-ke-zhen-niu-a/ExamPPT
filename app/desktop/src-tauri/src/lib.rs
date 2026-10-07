use std::{fs, path::Path, process::Command};

fn allowed_extension(path: &str, allowed: &[&str]) -> bool {
    Path::new(path)
        .extension()
        .and_then(|x| x.to_str())
        .map(|x| allowed.iter().any(|item| x.eq_ignore_ascii_case(item)))
        .unwrap_or(false)
}

#[tauri::command]
fn read_file_bytes(path: String) -> Result<Vec<u8>, String> {
    if !allowed_extension(&path, &["pdf", "png", "jpg", "jpeg"]) {
        return Err("Unsupported file type.".into());
    }
    fs::read(&path).map_err(|e| format!("Cannot read file: {e}"))
}

#[tauri::command]
fn read_text_file(path: String) -> Result<String, String> {
    if !allowed_extension(&path, &["json"]) {
        return Err("Only JSON text files are allowed.".into());
    }
    fs::read_to_string(&path).map_err(|e| format!("Cannot read text file: {e}"))
}

#[tauri::command]
fn open_parent_folder(path: String) -> Result<(), String> {
    let target = Path::new(&path);
    if !target.exists() {
        return Err("Path does not exist.".into());
    }
    let parent = target
        .parent()
        .ok_or_else(|| "Parent folder does not exist.".to_string())?;
    Command::new("explorer.exe")
        .arg(parent)
        .spawn()
        .map_err(|e| format!("Cannot open Explorer: {e}"))?;
    Ok(())
}

#[tauri::command]
fn smoke_test_pdf() -> Option<String> {
    std::env::var("EXAMPPT_TEST_PDF").ok()
}

#[tauri::command]
fn smoke_test_auto_build() -> bool {
    std::env::var("EXAMPPT_AUTO_BUILD")
        .map(|value| value == "1" || value.eq_ignore_ascii_case("true"))
        .unwrap_or(false)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            read_file_bytes,
            read_text_file,
            open_parent_folder,
            smoke_test_pdf,
            smoke_test_auto_build
        ])
        .run(tauri::generate_context!())
        .expect("error while running ExamPPT");
}
