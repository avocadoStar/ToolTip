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
$logPath = Join-Path $baseDir 'notify.log'

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
        default { return @("$Source 已停止", '请查看当前任务状态。') }
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

function Test-NotificationsEnabled {
    $config = Get-NotifyConfig
    if ($null -eq $config) {
        return $true
    }

    $enabled = $config.PSObject.Properties['notificationsEnabled']
    if ($null -eq $enabled) {
        return $true
    }

    if ($enabled.Value -is [bool]) {
        return [bool]$enabled.Value
    }

    return $true
}

function Write-NotifyLog {
    param(
        [Parameter(Mandatory)][string]$Decision,
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Event
    )

    $line = [string]::Join("`t", @(
        [DateTimeOffset]::Now.ToString('o'),
        "source=$Source",
        "event=$Event",
        "decision=$Decision"
    ))
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
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
            Background="#FAFBFD"
            BorderBrush="#E4E8F0"
            BorderThickness="1"
            CornerRadius="18">
        <Border.Effect>
            <DropShadowEffect Color="#8AA3C2"
                              BlurRadius="18"
                              ShadowDepth="3"
                              Opacity="0.18" />
        </Border.Effect>
        <Grid Margin="15,12,12,12">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="38" />
                <ColumnDefinition Width="*" />
                <ColumnDefinition Width="24" />
            </Grid.ColumnDefinitions>
            <Grid.RowDefinitions>
                <RowDefinition Height="24" />
                <RowDefinition Height="*" />
            </Grid.RowDefinitions>

            <Border Grid.Row="0"
                    Grid.RowSpan="2"
                    Grid.Column="0"
                    Width="24"
                    Height="24"
                    HorizontalAlignment="Left"
                    VerticalAlignment="Top"
                    Margin="0,2,0,0"
                    CornerRadius="7">
                <Border.Background>
                    <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                        <GradientStop Color="#4DA3FF" Offset="0" />
                        <GradientStop Color="#0A73F6" Offset="1" />
                    </LinearGradientBrush>
                </Border.Background>
                <Grid>
                    <Ellipse Width="12" Height="12" Fill="#FFFFFF" Opacity="0.96" />
                    <Ellipse Width="6" Height="6" Fill="#1368FF" HorizontalAlignment="Right" Margin="0,0,4,0" />
                    <Ellipse Width="4" Height="4" Fill="#BBD7FF" HorizontalAlignment="Left" Margin="7,0,0,0" />
                </Grid>
            </Border>

            <TextBlock Name="titleText"
                       Grid.Row="0"
                       Grid.Column="1"
                       VerticalAlignment="Center"
                       TextTrimming="CharacterEllipsis"
                       FontSize="14.5"
                       FontWeight="SemiBold"
                       Foreground="#1D1D1F" />

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
                    FontSize="17"
                    FontWeight="Light"
                    Foreground="#707075" />

            <TextBlock Name="messageText"
                       Grid.Row="1"
                       Grid.Column="1"
                       Grid.ColumnSpan="2"
                       VerticalAlignment="Top"
                       TextWrapping="Wrap"
                       TextTrimming="CharacterEllipsis"
                       FontSize="12.5"
                       LineHeight="16"
                       Foreground="#626268" />
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

Write-NotifyLog -Decision 'triggered' -Source $Source -Event $Event
$notice = Get-NoticeText -Source $Source -Event $Event
if (-not (Test-NotificationsEnabled)) {
    Write-NotifyLog -Decision 'skipped-disabled' -Source $Source -Event $Event
    return
}

Show-ToastNotice -Title $notice[0] -Message $notice[1]
Write-NotifyLog -Decision 'shown' -Source $Source -Event $Event

try {
    $audioPath = Resolve-AudioPath
    if ($null -ne $audioPath) {
        Play-NoticeSound -Path $audioPath
    }
}
catch {
    Write-NotifyLog -Decision 'audio-error' -Source $Source -Event $Event
}
"""
