# Cell 0 OS Homebrew Formula
# Place this in homebrew-cell0 repository or submit to homebrew-core

class Cell0 < Formula
  desc "Sovereign Edge Model Operating System"
  homepage "https://cell0.io"
  url "https://github.com/cell0-os/cell0/archive/refs/tags/v1.2.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "GPL-3.0"
  head "https://github.com/cell0-os/cell0.git", branch: "main"

  depends_on "python@3.11"
  depends_on "rust" => :build
  depends_on "ollama" => :optional

  resource "aiohttp" do
    url "https://files.pythonhosted.org/packages/aiohttp-3.9.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "websockets" do
    url "https://files.pythonhosted.org/packages/websockets-12.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "fastapi" do
    url "https://files.pythonhosted.org/packages/fastapi-0.104.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "uvicorn" do
    url "https://files.pythonhosted.org/packages/uvicorn-0.24.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/rich-13.7.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "typer" do
    url "https://files.pythonhosted.org/packages/typer-0.9.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    # Create virtual environment
    venv = virtualenv_create(libexec, "python3.11")
    
    # Install Python dependencies
    venv.pip_install resources
    
    # Install Cell 0
    venv.pip_install_and_link buildpath
    
    # Build Rust kernel
    cd "kernel" do
      system "cargo", "build", "--release"
      bin.install "target/release/cell0"
    end
    
    # Install scripts
    bin.install_symlink libexec/"bin/cell0ctl" => "cell0ctl"
    bin.install_symlink libexec/"bin/cell0d" => "cell0d"
    
    # Create state directory
    (var/"cell0").mkpath
    
    # Install service
    (buildpath/"cell0d.plist").write <<~EOS
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>#{plist_name}</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{opt_bin}/cell0d</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <true/>
        <key>StandardOutPath</key>
        <string>#{var}/log/cell0.log</string>
        <key>StandardErrorPath</key>
        <string>#{var}/log/cell0.log</string>
        <key>EnvironmentVariables</key>
        <dict>
          <key>CELL0_HOME</key>
          <string>#{opt_prefix}</string>
          <key>CELL0_STATE_DIR</key>
          <string>#{var}/cell0</string>
        </dict>
      </dict>
      </plist>
    EOS
    
    plist_path = "cell0d.plist"
    prefix.install plist_path
  end

  def post_install
    # Create necessary directories
    (var/"cell0/data").mkpath
    (var/"cell0/logs").mkpath
    (var/"cell0/config").mkpath
  end

  def caveats
    <<~EOS
      Cell 0 OS has been installed!
      
      To start Cell 0:
        brew services start cell0
      
      Or manually:
        cell0d
      
      To manage Cell 0:
        cell0ctl status
        cell0ctl start
        cell0ctl stop
      
      Web Interface:
        http://localhost:18800
      
      Configuration:
        #{var}/cell0/config/
    EOS
  end

  service do
    run [opt_bin/"cell0d"]
    keep_alive true
    log_path var/"log/cell0.log"
    error_log_path var/"log/cell0.log"
    environment_variables(
      CELL0_HOME: opt_prefix,
      CELL0_STATE_DIR: var/"cell0",
      CELL0_ENV: "production"
    )
  end

  test do
    # Test CLI
    assert_match "Cell 0 OS", shell_output("#{bin}/cell0ctl --version")
    
    # Test API is reachable (daemon not started in test)
    # assert_equal "healthy", shell_output("#{bin}/cell0ctl health")
  end
end
