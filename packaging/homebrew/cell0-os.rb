# Cell 0 OS Homebrew Formula
# Usage: brew tap cell0-os/cell0 && brew install cell0-os

class Cell0Os < Formula
  desc "Sovereign Edge Model Operating System"
  homepage "https://cell0.io"
  url "https://github.com/cell0-os/cell0/archive/refs/tags/v1.2.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "GPL-3.0"
  version "1.2.0"

  depends_on "python@3.11"
  depends_on "rust" => :build

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

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/pyyaml-6.0.1.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/pydantic-2.5.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/httpx-0.25.0.tar.gz"
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

  resource "prometheus-client" do
    url "https://files.pythonhosted.org/packages/prometheus_client-0.19.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyjwt" do
    url "https://files.pythonhosted.org/packages/PyJWT-2.8.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "cryptography" do
    url "https://files.pythonhosted.org/packages/cryptography-41.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    # Create virtual environment
    venv = virtualenv_create(libexec, "python3.11")
    
    # Install Python dependencies
    venv.pip_install resources
    
    # Install Cell 0
    venv.pip_install_and_link buildpath
    
    # Create wrapper scripts
    (bin/"cell0d").write_env_script libexec/"bin/cell0d", {
      CELL0_HOME:            var/"cell0",
      CELL0_STATE_DIR:       var/"cell0/data",
      CELL0_CONFIG_DIR:      etc/"cell0",
    }
    
    (bin/"cell0ctl").write_env_script libexec/"bin/cell0ctl", {
      CELL0_HOME:            var/"cell0",
      CELL0_STATE_DIR:       var/"cell0/data",
      CELL0_CONFIG_DIR:      etc/"cell0",
    }
    
    # Install LaunchDaemon plist
    plist_file = "com.cell0.daemon.plist"
    (buildpath/plist_file).write <<~EOS
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>com.cell0.daemon</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{opt_bin}/cell0d</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <true/>
        <key>StandardOutPath</key>
        <string>#{var}/log/cell0/cell0d.log</string>
        <key>StandardErrorPath</key>
        <string>#{var}/log/cell0/cell0d.error.log</string>
      </dict>
      </plist>
    EOS
    
    (prefix/"#{plist_file}").write (buildpath/plist_file).read
  end

  def post_install
    # Create necessary directories
    (var/"cell0/data").mkpath
    (var/"cell0/logs").mkpath
    (etc/"cell0").mkpath
    (var/"log/cell0").mkpath
  end

  def caveats
    <<~EOS
      Cell 0 OS has been installed!

      To start the daemon:
        brew services start cell0-os

      Or manually:
        cell0d start

      Web interfaces:
        Web UI:    http://localhost:18800
        WebSocket: ws://localhost:18801
        Metrics:   http://localhost:18802/metrics

      CLI:
        cell0ctl --help

      Configuration:
        #{etc}/cell0

      Data:
        #{var}/cell0/data

      Logs:
        #{var}/log/cell0
    EOS
  end

  service do
    run [opt_bin/"cell0d"]
    keep_alive true
    log_path var/"log/cell0/cell0d.log"
    error_log_path var/"log/cell0/cell0d.error.log"
    environment_variables PATH: std_service_path_env
  end

  test do
    system "#{bin}/cell0ctl", "--version"
    system "#{bin}/cell0d", "--version"
  end
end
