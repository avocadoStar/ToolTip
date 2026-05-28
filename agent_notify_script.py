from __future__ import annotations


def get_notify_script_content() -> str:
    return r"""param(
    [ValidateSet('Codex', 'Claude')]
    [string]$Source = 'Codex',

    [string]$Event = 'Stop',

    [string]$ManagedBy = 'AgentNotifyConfigurator'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Xaml

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $baseDir 'config.json'

function Get-NotifyConfig {
    if (Test-Path -LiteralPath $configPath) {
        return Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    }

    return $null
}

function Get-NoticeText {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Event
    )

    switch ("$Source`:$Event") {
        'Codex:PermissionRequest' { return @('Codex 等待确认', '有权限或命令需要你处理。') }
        'Claude:Notification' { return @('Claude 等待输入', 'Claude Code 正在等待输入或确认。') }
        'Claude:Stop' { return @('Claude 已停止', '当前任务轮次已经结束。') }
        default { return @("$Source 已停止", '请回到 VS Code 查看当前状态。') }
    }
}

function Resolve-AudioPath {
    $config = Get-NotifyConfig
    if ($null -ne $config) {
        $managedAudio = $config.PSObject.Properties['managedAudio']
        if ($null -ne $managedAudio -and $managedAudio.Value) {
            if (Test-Path -LiteralPath $managedAudio.Value) {
                return [string]$managedAudio.Value
            }
            throw "Managed audio file does not exist: $($managedAudio.Value)"
        }
    }

    foreach ($name in @('completed.wav', 'completed.mp3')) {
        $candidate = Join-Path $baseDir $name
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Test-SuppressWhenVSCodeFocused {
    $config = Get-NotifyConfig
    if ($null -eq $config) {
        return $true
    }

    if ($null -eq $config.PSObject.Properties['suppressWhenVSCodeFocused']) {
        return $true
    }

    return [bool]$config.suppressWhenVSCodeFocused
}

function Get-ForegroundProcessName {
    $signature = @'
[DllImport("user32.dll")]
public static extern System.IntPtr GetForegroundWindow();
[DllImport("user32.dll")]
public static extern uint GetWindowThreadProcessId(System.IntPtr hWnd, out uint processId);
'@

    if (-not ([System.Management.Automation.PSTypeName]'AgentNotify.ForegroundWindow').Type) {
        Add-Type -MemberDefinition $signature -Name "ForegroundWindow" -Namespace "AgentNotify"
    }

    $handle = [AgentNotify.ForegroundWindow]::GetForegroundWindow()
    if ($handle -eq [IntPtr]::Zero) {
        return ''
    }

    [uint32]$processId = 0
    [AgentNotify.ForegroundWindow]::GetWindowThreadProcessId($handle, [ref]$processId) | Out-Null
    if ($processId -eq 0) {
        return ''
    }

    return (Get-Process -Id ([int]$processId)).ProcessName
}

function Test-VSCodeForeground {
    $processName = Get-ForegroundProcessName
    return $processName -in @('Code', 'Code - Insiders')
}

function Play-NoticeSound {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Audio file does not exist: $Path"
    }

    $signature = @'
[DllImport("winmm.dll", CharSet = CharSet.Unicode)]
public static extern int mciSendString(string command, System.Text.StringBuilder returnValue, int returnLength, System.IntPtr winHandle);
'@

    if (-not ("WinMM" -as [type])) {
        Add-Type -MemberDefinition $signature -Name "WinMM" -Namespace "AgentNotify"
    }

    $alias = "agent_notice_" + [Guid]::NewGuid().ToString("N")
    $openResult = [AgentNotify.WinMM]::mciSendString("open `"$Path`" alias $alias", $null, 0, [IntPtr]::Zero)
    if ($openResult -ne 0) {
        throw "Failed to open audio file: $Path"
    }

    try {
        $playResult = [AgentNotify.WinMM]::mciSendString("play $alias wait", $null, 0, [IntPtr]::Zero)
        if ($playResult -ne 0) {
            throw "Failed to play audio file: $Path"
        }
    }
    finally {
        [AgentNotify.WinMM]::mciSendString("close $alias", $null, 0, [IntPtr]::Zero) | Out-Null
    }
}

function Show-ToastNotice {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$Message
    )

    [xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="AI Hook 提示"
        Width="340"
        Height="92"
        WindowStyle="None"
        AllowsTransparency="True"
        ResizeMode="NoResize"
        ShowInTaskbar="False"
        Background="Transparent"
        FontFamily="Microsoft YaHei UI"
        SnapsToDevicePixels="True"
        UseLayoutRounding="True">
    <Border Name="macOSNoticeCard"
            Background="#F8FBFF"
            BorderBrush="#D9E4F2"
            BorderThickness="1"
            CornerRadius="18">
        <Border.Effect>
            <DropShadowEffect Color="#8AA3C2"
                              BlurRadius="20"
                              ShadowDepth="4"
                              Opacity="0.20" />
        </Border.Effect>
        <Grid Margin="16,13,14,13">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="44" />
                <ColumnDefinition Width="*" />
                <ColumnDefinition Width="26" />
            </Grid.ColumnDefinitions>
            <Grid.RowDefinitions>
                <RowDefinition Height="25" />
                <RowDefinition Height="*" />
            </Grid.RowDefinitions>

            <Border Grid.Row="0"
                    Grid.RowSpan="2"
                    Grid.Column="0"
                    Width="30"
                    Height="30"
                    HorizontalAlignment="Left"
                    VerticalAlignment="Center"
                    CornerRadius="9">
                <Border.Background>
                    <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                        <GradientStop Color="#2F8BFF" Offset="0" />
                        <GradientStop Color="#005BFF" Offset="1" />
                    </LinearGradientBrush>
                </Border.Background>
                <Grid>
                    <Ellipse Width="16" Height="16" Fill="#FFFFFF" Opacity="0.96" />
                    <Ellipse Width="8" Height="8" Fill="#1368FF" HorizontalAlignment="Right" Margin="0,0,4,0" />
                    <Ellipse Width="5" Height="5" Fill="#BBD7FF" HorizontalAlignment="Left" Margin="8,0,0,0" />
                </Grid>
            </Border>

            <TextBlock Name="titleText"
                       Grid.Row="0"
                       Grid.Column="1"
                       VerticalAlignment="Bottom"
                       TextTrimming="CharacterEllipsis"
                       FontSize="15"
                       FontWeight="SemiBold"
                       Foreground="#111827" />

            <Button Name="closeButton"
                    Grid.Row="0"
                    Grid.Column="2"
                    Width="22"
                    Height="22"
                    HorizontalAlignment="Right"
                    VerticalAlignment="Top"
                    Content="×"
                    Cursor="Hand"
                    Background="Transparent"
                    BorderBrush="Transparent"
                    BorderThickness="0"
                    Padding="0"
                    FontSize="18"
                    FontWeight="Light"
                    Foreground="#3F3F46" />

            <TextBlock Name="messageText"
                       Grid.Row="1"
                       Grid.Column="1"
                       Grid.ColumnSpan="2"
                       VerticalAlignment="Top"
                       TextWrapping="Wrap"
                       TextTrimming="CharacterEllipsis"
                       FontSize="12"
                       LineHeight="16"
                       Foreground="#3F3F46" />
        </Grid>
    </Border>
</Window>
'@

    $reader = [System.Xml.XmlNodeReader]::new($xaml)
    $window = [System.Windows.Markup.XamlReader]::Load($reader)
    $window.TopMost = $true

    $window.FindName('titleText').Text = $Title
    $window.FindName('messageText').Text = $Message
    $window.FindName('closeButton').Add_Click({ $window.Close() })

    $workingArea = [System.Windows.SystemParameters]::WorkArea
    $window.Left = $workingArea.Right - $window.Width - 22
    $window.Top = $workingArea.Bottom - $window.Height - 22

    $timer = [System.Windows.Threading.DispatcherTimer]::new()
    $timer.Interval = [TimeSpan]::FromSeconds(5)
    $timer.Add_Tick({
        $timer.Stop()
        $window.Close()
    })

    $window.Add_Closed({
        $timer.Stop()
    })
    $window.Add_ContentRendered({
        $timer.Start()
        $window.Activate() | Out-Null
    })
    $window.ShowDialog() | Out-Null
}

$notice = Get-NoticeText -Source $Source -Event $Event
if ((Test-SuppressWhenVSCodeFocused) -and (Test-VSCodeForeground)) {
    return
}

$audioPath = Resolve-AudioPath
if ($null -ne $audioPath) {
    Play-NoticeSound -Path $audioPath
}
Show-ToastNotice -Title $notice[0] -Message $notice[1]
"""
