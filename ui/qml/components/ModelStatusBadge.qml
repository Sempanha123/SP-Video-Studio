import QtQuick 2.15

StatusBadge {
    property string modelStatus: "not_installed"
    text: modelStatus.replace(/_/g, " ").replace(/\b\w/g, function(ch) { return ch.toUpperCase() })
    status: modelStatus
}
